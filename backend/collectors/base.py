from abc import ABC, abstractmethod
from dataclasses import dataclass

try:
    from ..models import PlatformType, Product
except ImportError:
    from models import PlatformType, Product


@dataclass(frozen=True)
class CollectorMetadata:
    source_name: str
    platform: PlatformType
    requires_api_key: bool = False
    enabled: bool = True


class BaseCollector(ABC):
    metadata: CollectorMetadata

    @abstractmethod
    def collect(self, query: str | None = None, limit: int = 50) -> list[Product]:
        """Collect normalized products from one source."""
