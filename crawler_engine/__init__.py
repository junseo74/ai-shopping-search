from typing import TYPE_CHECKING

from .models import CrawlRequest, CrawlResult, CrawledProduct, SourceMetadata

__all__ = [
    "CrawlerEngine",
    "CrawlRequest",
    "CrawlResult",
    "CrawledProduct",
    "SourceMetadata",
]

if TYPE_CHECKING:
    from .engine import CrawlerEngine


def __getattr__(name: str):
    if name == "CrawlerEngine":
        from .engine import CrawlerEngine

        return CrawlerEngine
    raise AttributeError(f"module 'crawler_engine' has no attribute {name!r}")
