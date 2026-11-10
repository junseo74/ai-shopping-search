from collections import Counter
from copy import deepcopy
from dataclasses import asdict
from datetime import timedelta
import ipaddress
from urllib.parse import urlsplit

from .contracts import CollectionError, SourcePolicy, utc_now
from .storage import digest
from .quality import normalized_product


def public_url(value):
    try:
        parsed = urlsplit(str(value or ""))
        if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
            return False
        hostname = parsed.hostname.lower().rstrip(".")
        parsed.port  # Reject malformed ports as well as malformed hosts.
        if hostname == "localhost" or "." not in hostname or hostname.endswith((".localhost", ".local", ".internal")):
            return False
        try:
            return ipaddress.ip_address(hostname).is_global
        except ValueError:
            return True
    except ValueError:
        return False


class CollectionRunner:
    def __init__(self, adapter, policy: SourcePolicy, state, sink, clock=utc_now):
        self.adapter, self.policy, self.state, self.sink, self.clock = adapter, policy, state, sink, clock

    def run(self, query, job_id, max_items=3, page_size=3, max_pages=1, purpose="validation", since=None):
        if (any(type(value) is not int for value in (max_items, page_size, max_pages))
                or page_size < 1 or max_pages < 1 or page_size > 1000):
            raise ValueError("Invalid bounded batch configuration")
        self.policy.check(purpose, max_items)
        if self.adapter.source != self.policy.source:
            raise CollectionError("source_policy_mismatch")
        signature = digest([self.adapter.source, query, purpose, since, max_items, page_size])
        policy_signature = digest(asdict(self.policy))
        adapter_context = digest(getattr(self.adapter, "checkpoint_context", None))
        with self.state.lock():
            checkpoint = self.state.load_checkpoint(job_id)
            if checkpoint and checkpoint["signature"] != signature:
                raise ValueError("Job parameters changed; use a new job_id")
            if checkpoint and (checkpoint.get("policy_signature", policy_signature) != policy_signature
                               or checkpoint.get("adapter_context", adapter_context) != adapter_context):
                raise ValueError("Source policy or adapter context changed; use a new job_id")
            stats = checkpoint["stats"] if checkpoint else {
                "received": 0, "emitted": 0, "invalid": 0, "duplicates": 0,
                "unchanged": 0, "pages": 0, "missing_fields": {}, "reasons": {}}
            cursor = checkpoint["cursor"] if checkpoint else None
            done = checkpoint.get("done", False) if checkpoint else False
            cursor_history = set(checkpoint.get("cursor_history", [])) if checkpoint else set()
            cursor_history.add(digest(cursor))
            errors = []
            for _ in range(max_pages):
                if done or stats["received"] >= max_items:
                    break
                limit = min(page_size, max_items - stats["received"])
                try:
                    page = self.adapter.fetch_page(query, cursor, limit, since)
                    if (type(page.rejected) is not int or page.rejected < 0
                            or not isinstance(page.offers, list)
                            or (page.next_cursor is not None and not isinstance(page.next_cursor, str))):
                        raise CollectionError("invalid_page")
                    if len(page.offers) + page.rejected > limit:
                        raise CollectionError("page_limit_violation")
                    if page.next_cursor is not None and digest(page.next_cursor) in cursor_history:
                        raise CollectionError("pagination_loop")
                    if not page.offers and not page.rejected and page.next_cursor is not None:
                        raise CollectionError("empty_page_with_cursor")
                    now = self.clock()
                    expires_at = (now + timedelta(seconds=self.policy.retention_seconds)).isoformat()
                    prepared, seen = [], set()
                    missing, reasons = Counter(), Counter()
                    if page.rejected:
                        reasons["adapter_rejected"] = page.rejected
                    duplicates = 0
                    for offer in page.offers:
                        product = offer.product
                        for field in ("product_name", "price", "currency", "platform", "product_url", "seller",
                                      "image_url", "category", "condition", "collected_at"):
                            if getattr(product, field) is None or getattr(product, field) == "":
                                missing[field] += 1
                        if (not isinstance(offer.product_id, str) or not offer.product_id.strip()
                                or not isinstance(offer.offer_id, str) or not offer.offer_id.strip()):
                            missing["source_product_id"] += not bool(offer.product_id)
                            reasons["identity_or_name_missing"] += 1
                            continue
                        reason = None
                        try:
                            product = normalized_product(product)
                        except CollectionError as error:
                            reason = error.category
                        if reason is None and not public_url(product.product_url):
                            reason = "invalid_product_url"
                        elif reason is None and product.image_url is not None and not public_url(product.image_url):
                            reason = "invalid_image_url"
                        if reason:
                            reasons[reason] += 1
                            continue
                        key = digest([self.adapter.source, offer.product_id, offer.offer_id, product.currency])
                        if key in seen:
                            duplicates += 1
                            continue
                        seen.add(key)
                        payload = product.model_dump(mode="json")
                        payload["data_source"] = self.adapter.source
                        for field in self.policy.omitted_fields:
                            if field in payload:
                                payload[field] = None
                        payload["collected_at"] = now.isoformat()
                        payload["source_observed_at"] = now.isoformat()
                        # Observation timestamps and local DB primary key are not content.
                        content = {k: v for k, v in payload.items() if k not in ("collected_at", "source_observed_at", "id")}
                        fingerprint = digest(content)
                        event_id = digest([job_id, cursor, key, fingerprint])
                        prepared.append({"schema_version": "1.0", "event_id": event_id,
                            "source": self.adapter.source, "source_product_id": offer.product_id,
                            "source_offer_id": offer.offer_id, "offer_key": key,
                            "identity_basis": offer.identity_basis, "fingerprint": fingerprint,
                            "observed_at": now.isoformat(), "expires_at": expires_at,
                            "policy_reference": self.policy.terms_url, "purpose": purpose,
                            "synthetic": self.policy.synthetic, "product": payload})
                    versions = self.state.versions([row["offer_key"] for row in prepared], now)
                    changed = [row for row in prepared if versions.get(row["offer_key"]) != row["fingerprint"]]
                    batch_id = digest([job_id, cursor, [row["event_id"] for row in changed]])
                    if changed:
                        self.sink.write_batch(batch_id, changed)
                    self.state.commit_versions({row["offer_key"]: {"fingerprint": row["fingerprint"],
                        "expires_at": expires_at} for row in changed})
                    next_stats = deepcopy(stats)
                    next_stats["received"] += len(page.offers) + page.rejected
                    next_stats["invalid"] += sum(reasons.values())
                    next_stats["duplicates"] += duplicates
                    next_stats["unchanged"] += len(prepared) - len(changed)
                    next_stats["emitted"] += len(changed)
                    next_stats["pages"] += 1
                    for label, counts in (("missing_fields", missing), ("reasons", reasons)):
                        next_stats[label] = dict(Counter(next_stats[label]) + counts)
                    next_cursor = page.next_cursor
                    next_history = cursor_history | ({digest(next_cursor)} if next_cursor is not None else set())
                    next_done = next_cursor is None or next_stats["received"] >= max_items
                    self.state.save_checkpoint(job_id, {"signature": signature, "cursor": next_cursor,
                        "done": next_done, "stats": next_stats, "cursor_history": sorted(next_history),
                        "policy_signature": policy_signature, "adapter_context": adapter_context,
                        "updated_at": now.isoformat()})
                    stats, cursor, done, cursor_history = next_stats, next_cursor, next_done, next_history
                except CollectionError as error:
                    errors.append({"category": error.category, "http_status": error.http_status,
                                   "retry_after": error.retry_after})
                    break
                except Exception as error:
                    errors.append({"category": "processing_or_storage_error", "type": type(error).__name__})
                    break
            received = stats["received"]
            return {"source": self.adapter.source, "job_id": job_id, "done": done,
                "status": "failed" if errors else "completed" if done else "paused_at_page_budget",
                "synthetic": self.policy.synthetic, "stats": stats, "errors": errors,
                "duplicate_rate": stats["duplicates"] / received if received else 0,
                "missing_field_rates": {k: v / received for k, v in stats["missing_fields"].items()} if received else {},
                "checked_at": self.clock().isoformat()}
