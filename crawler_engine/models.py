from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass(frozen=True)
class CrawlRequest:
    query: str
    max_price: Optional[int] = None
    include_used: bool = False
    country: str = "KR"
    limit: int = 20

    def __post_init__(self) -> None:
        if not self.query or not self.query.strip():
            raise ValueError("CrawlRequest.query is required.")
        if self.limit < 1:
            raise ValueError("CrawlRequest.limit must be at least 1.")
        if self.max_price is not None and self.max_price < 0:
            raise ValueError("CrawlRequest.max_price must be greater than or equal to 0.")


@dataclass(frozen=True)
class SourceMetadata:
    source: str
    display_name: str
    country: str = "KR"
    used_only: bool = False
    base_url: str = ""
    default_condition: str = "unknown"
    product_url_hints: tuple[str, ...] = ()
    product_identity_params: tuple[str, ...] = ()
    canonical_product_url_hints: tuple[str, ...] = ()
    excluded_url_hints: tuple[str, ...] = ()
    ad_url_hints: tuple[str, ...] = ()
    allow_ad_products: bool = False
    require_positive_price: bool = False

    def __post_init__(self) -> None:
        if self.default_condition == "unknown" and self.used_only:
            object.__setattr__(self, "default_condition", "used")


@dataclass
class ProductCandidate:
    product_name: Optional[str] = None
    price_text: Optional[str] = None
    price: Optional[int] = None
    currency: str = "KRW"
    source: Optional[str] = None
    seller: Optional[str] = None
    condition: Optional[str] = None
    country: str = "KR"
    product_url: Optional[str] = None
    image_url: Optional[str] = None
    description: Optional[str] = None
    confidence: float = 0
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class CrawledProduct:
    product_name: str
    price: Optional[int]
    currency: str
    source: str
    seller: Optional[str]
    condition: str
    country: str
    product_url: Optional[str]
    image_url: Optional[str]
    description: Optional[str]
    collected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["collected_at"] = self.collected_at.isoformat()
        return payload


@dataclass
class CrawlResult:
    query: str
    source: Optional[str]
    products: list[CrawledProduct]
    status: str = "success"
    error: Optional[str] = None
    errors: list[str] = field(default_factory=list)
    debug: dict[str, Any] = field(default_factory=dict)
    collected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "source": self.source,
            "status": self.status,
            "product_count": len(self.products),
            "error": self.error,
            "errors": self.errors,
            "debug": self.debug,
            "collected_at": self.collected_at.isoformat(),
            "products": [product.to_dict() for product in self.products],
        }
