from __future__ import annotations

from urllib.parse import quote

from ..models import CrawlRequest, SourceMetadata


class MusinsaSource:
    metadata = SourceMetadata(
        source="musinsa",
        display_name="MUSINSA",
        country="KR",
        used_only=False,
        base_url="https://www.musinsa.com",
        default_condition="new",
        product_url_hints=("musinsa.com/products/", "/products/"),
        canonical_product_url_hints=("musinsa.com/products/",),
        require_positive_price=True,
    )

    def build_search_url(self, request: CrawlRequest) -> str:
        encoded = quote(request.query.strip())
        return f"{self.metadata.base_url}/search/goods?keyword={encoded}&gf=A"
