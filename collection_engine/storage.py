"""Local reference checkpoint/outbox, no SQL connection.

One writer per state directory. Production distributed workers need a shared
transactional state implementation, not a shared network filesystem.
"""
from contextlib import contextmanager
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import tempfile


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
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    def save_checkpoint(self, job_id, value):
        atomic_json(self.directory / "jobs" / (digest(job_id) + ".json"), value)

    def versions(self, keys, now):
        result = {}
        for prefix in {key[:3] for key in keys}:
            path = self.directory / "versions" / (prefix + ".json")
            bucket = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
            for key in keys:
                value = bucket.get(key)
                if value and datetime.fromisoformat(value["expires_at"]) > now:
                    result[key] = value["fingerprint"]
        return result

    def commit_versions(self, entries):
        for prefix in {key[:3] for key in entries}:
            path = self.directory / "versions" / (prefix + ".json")
            bucket = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
            bucket.update({key: value for key, value in entries.items() if key[:3] == prefix})
            atomic_json(path, bucket)


class JsonlSink:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def write_batch(self, batch_id, records):
        path = self.directory / (digest(batch_id) + ".jsonl")
        # An at-least-once replay may have newer observed_at. Event IDs remain
        # stable for the same job/page/offer/content. Existing accepted batch wins.
        if path.exists():
            old = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            if [row["event_id"] for row in old] != [row["event_id"] for row in records]:
                raise ValueError("Outbox batch identity conflict")
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
                    record = json.loads(line)
                    if datetime.fromisoformat(record["expires_at"]) > now:
                        yield record
