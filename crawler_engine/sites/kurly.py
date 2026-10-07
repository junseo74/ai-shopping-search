from __future__ import annotations

from urllib.parse import quote

from ..models import CrawlRequest, SourceMetadata


class KurlySource:
    metadata = SourceMetadata(
        source="kurly",
        display_name="Kurly",
        country="KR",
        used_only=False,
        base_url="https://www.kurly.com",
        default_condition="new",
        product_url_hints=("kurly.com/goods/", "/goods/"),
        canonical_product_url_hints=("kurly.com/goods/",),
        require_positive_price=True,
    )

    def build_search_url(self, request: CrawlRequest) -> str:
        encoded = quote(request.query.strip())
        return f"{self.metadata.base_url}/search?sword={encoded}"
