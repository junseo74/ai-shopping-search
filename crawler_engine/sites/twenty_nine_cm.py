from __future__ import annotations

from urllib.parse import quote

from ..models import CrawlRequest, SourceMetadata


class TwentyNineCmSource:
    metadata = SourceMetadata(
        source="29cm",
        display_name="29CM",
        country="KR",
        used_only=False,
        base_url="https://www.29cm.co.kr",
        default_condition="new",
        product_url_hints=("product.29cm.co.kr/catalog/", "/catalog/"),
        canonical_product_url_hints=("product.29cm.co.kr/catalog/",),
        require_positive_price=True,
    )

    def build_search_url(self, request: CrawlRequest) -> str:
        encoded = quote(request.query.strip())
        return f"{self.metadata.base_url}/store/search?keyword={encoded}&sort=RECOMMENDED&page=1"
