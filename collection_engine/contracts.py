from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from backend.models import Product


def utc_now():
    return datetime.now(timezone.utc)


@dataclass
class Offer:
    product: Product
    product_id: str
    offer_id: str
    identity_basis: str = "provider_id"


@dataclass
class Page:
    offers: list[Offer]
    next_cursor: str | None = None
    rejected: int = 0


class Adapter(Protocol):
    source: str

    def fetch_page(self, query: str, cursor: str | None, limit: int,
                   since: str | None = None) -> Page: ...


class Sink(Protocol):
    def write_batch(self, batch_id: str, records: list[dict]) -> None:
        """Durably accept the batch before returning; consumer upserts event_id."""
        ...


class StateStore(Protocol):
    """Replace the local store with a transactional implementation after approval."""
    def lock(self): ...
    def load_checkpoint(self, job_id: str) -> dict | None: ...
    def save_checkpoint(self, job_id: str, value: dict) -> None: ...
    def versions(self, keys: list[str], now: datetime) -> dict[str, str]: ...
    def commit_versions(self, entries: dict) -> None: ...


@dataclass(frozen=True)
class SourcePolicy:
    source: str
    method: str
    lookup_allowed: bool = False
    terms_url: str = ""
    credential_env: tuple[str, ...] = ()
    purposes: tuple[str, ...] = ("validation",)
    validation_limit: int = 3
    retention_seconds: int = 3600
    bulk_approved: bool = False
    synthetic: bool = False
    omitted_fields: tuple[str, ...] = ("seller", "region", "detail_description")

    def check(self, purpose: str, max_items: int):
        if not self.lookup_allowed or purpose not in self.purposes or not self.terms_url:
            raise CollectionError("policy_restriction")
        if self.retention_seconds <= 0:
            raise CollectionError("storage_permission_required")
        if max_items < 1 or (not self.bulk_approved and max_items > self.validation_limit):
            raise CollectionError("bulk_permission_required")


class CollectionError(RuntimeError):
    def __init__(self, category: str, http_status: int | None = None, retry_after: float | None = None):
        self.category, self.http_status, self.retry_after = category, http_status, retry_after
        # Never interpolate exception bodies, credential-bearing URLs or headers.
        super().__init__(category + (f" (HTTP {http_status})" if http_status else ""))
