"""Local reference checkpoint/outbox, no SQL connection.

One writer per state directory. Production distributed workers need a shared
transactional state implementation, not a shared network filesystem.
"""
from contextlib import contextmanager
from datetime import datetime
import hashlib
import json
import math
import re
import os
from pathlib import Path
import tempfile

from backend.models import Product
from .contracts import CollectionError


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _read_object(path, category):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError
        return value
    except (ValueError, UnicodeError):
        raise CollectionError(category) from None


def _timestamp(value):
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("Timestamp requires a timezone")
    return parsed


def _hash(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def validate_record(record):
    """Check persisted envelopes and content hashes; never repair them silently."""
    try:
        if not isinstance(record, dict) or record.get("schema_version") != "1.0":
            raise ValueError
        for field in ("event_id", "offer_key", "fingerprint"):
            if not _hash(record.get(field)):
                raise ValueError
        for field in ("source", "source_product_id", "source_offer_id"):
            if not isinstance(record.get(field), str) or not record[field].strip():
                raise ValueError
        payload = record["product"]
        Product.model_validate(payload)
        price = payload["price"]
        if isinstance(price, bool) or not isinstance(price, (int, float)) or not math.isfinite(price) or price < 0:
            raise ValueError
        if not re.fullmatch(r"[A-Z]{3}", payload["currency"]):
            raise ValueError
        if payload.get("data_source") != record["source"]:
            raise ValueError
        content = {key: value for key, value in payload.items() if key not in ("collected_at", "source_observed_at", "id")}
        if digest(content) != record["fingerprint"]:
            raise ValueError
        if digest([record["source"], record["source_product_id"], record["source_offer_id"], payload["currency"]]) != record["offer_key"]:
            raise ValueError
        if _timestamp(record["expires_at"]) <= _timestamp(record["observed_at"]):
            raise ValueError
        _timestamp(payload["collected_at"])
    except (ValueError, TypeError, KeyError, OverflowError):
        raise CollectionError("outbox_corrupt") from None
    return record


def _replay_content(record):
    result = {key: value for key, value in record.items() if key not in ("observed_at", "expires_at", "product")}
    result["product"] = {key: value for key, value in record["product"].items()
                         if key not in ("collected_at", "source_observed_at", "id")}
    return result


class FileState:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def lock(self):
        path = self.directory / "writer.lock"
        fd = os.open(path, os.O_CREAT | os.O_RDWR)
        try:
            if os.fstat(fd).st_size == 0:
                os.write(fd, b"0")
            os.lseek(fd, 0, os.SEEK_SET)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            try:
                yield
            finally:
                os.lseek(fd, 0, os.SEEK_SET)
                if os.name == "nt":
                    msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)

    def load_checkpoint(self, job_id):
        path = self.directory / "jobs" / (digest(job_id) + ".json")
        if not path.exists():
            return None
        value = _read_object(path, "checkpoint_corrupt")
        try:
            if (not _hash(value["signature"]) or type(value["done"]) is not bool
                    or (value["cursor"] is not None and not isinstance(value["cursor"], str))):
                raise ValueError
            stats = value["stats"]
            for field in ("received", "emitted", "invalid", "duplicates", "unchanged", "pages"):
                if type(stats[field]) is not int or stats[field] < 0:
                    raise ValueError
            for field in ("missing_fields", "reasons"):
                if not isinstance(stats[field], dict) or any(type(count) is not int or count < 0 for count in stats[field].values()):
                    raise ValueError
            history = value.get("cursor_history", [])
            if not isinstance(history, list) or any(not _hash(item) for item in history):
                raise ValueError
        except (ValueError, KeyError, TypeError):
            raise CollectionError("checkpoint_corrupt") from None
        return value

    def save_checkpoint(self, job_id, value):
        atomic_json(self.directory / "jobs" / (digest(job_id) + ".json"), value)

    def versions(self, keys, now):
        result = {}
        for prefix in {key[:3] for key in keys}:
            path = self.directory / "versions" / (prefix + ".json")
            bucket = _read_object(path, "version_index_corrupt") if path.exists() else {}
            for key in keys:
                value = bucket.get(key)
                if value is not None:
                    try:
                        if not isinstance(value, dict) or not _hash(value["fingerprint"]):
                            raise ValueError
                        expires = _timestamp(value["expires_at"])
                    except (ValueError, TypeError, KeyError):
                        raise CollectionError("version_index_corrupt") from None
                    if expires > now:
                        result[key] = value["fingerprint"]
        return result

    def commit_versions(self, entries):
        for prefix in {key[:3] for key in entries}:
            path = self.directory / "versions" / (prefix + ".json")
            bucket = _read_object(path, "version_index_corrupt") if path.exists() else {}
            bucket.update({key: value for key, value in entries.items() if key[:3] == prefix})
            atomic_json(path, bucket)


class JsonlSink:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def write_batch(self, batch_id, records):
        for record in records:
            validate_record(record)
        path = self.directory / (digest(batch_id) + ".jsonl")
        # An at-least-once replay may have newer observed_at. Event IDs remain
        # stable for the same job/page/offer/content. Existing accepted batch wins.
        if path.exists():
            try:
                old = [validate_record(json.loads(line)) for line in path.read_text(encoding="utf-8").splitlines()]
            except (ValueError, UnicodeError):
                raise CollectionError("outbox_corrupt") from None
            if [_replay_content(row) for row in old] != [_replay_content(row) for row in records]:
                raise CollectionError("outbox_identity_conflict")
            return
        fd, temporary = tempfile.mkstemp(prefix=".pending-", dir=self.directory)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                for record in records:
                    stream.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def iter_unexpired(self, now):
        for path in sorted(self.directory.glob("*.jsonl")):
            with path.open(encoding="utf-8") as stream:
                for line in stream:
                    try:
                        record = validate_record(json.loads(line))
                    except (ValueError, UnicodeError):
                        raise CollectionError("outbox_corrupt") from None
                    if _timestamp(record["expires_at"]) > now:
                        yield record
