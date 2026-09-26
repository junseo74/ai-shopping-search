import json
from pathlib import Path

from .base import BaseCollector, CollectorMetadata

try:
    from ..models import PlatformType, Product
except ImportError:
    from models import PlatformType, Product


class TestFixtureCollector(BaseCollector):
    metadata = CollectorMetadata(
        source_name="test_fixture",
        platform=PlatformType.TEST,
        requires_api_key=False,
    )

    def __init__(self, fixture_path: Path | None = None):
        self.fixture_path = fixture_path or Path(__file__).resolve().parents[1] / "data" / "test_products.json"

    def collect(self, query: str | None = None, limit: int = 50) -> list[Product]:
        raw_products = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        products = [Product(**item) for item in raw_products]
        if query:
            lowered = query.lower()
            products = [
                product
                for product in products
                if lowered in product.product_name.lower()
                or (product.category and lowered in product.category.lower())
                or lowered in product.seller.lower()
            ]
        return products[:limit]
