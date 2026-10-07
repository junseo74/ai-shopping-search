from __future__ import annotations

from urllib.parse import quote

from ..models import CrawlRequest, SourceMetadata


class LotteOnSource:
    metadata = SourceMetadata(
        source="lotteon",
        display_name="LotteON",
        country="KR",
        used_only=False,
        base_url="https://www.lotteon.com",
        default_condition="new",
        product_url_hints=("/p/product/LO",),
        canonical_product_url_hints=("www.lotteon.com/p/product/LO",),
        require_positive_price=True,
    )

    def build_search_url(self, request: CrawlRequest) -> str:
        encoded = quote(request.query.strip())
        return f"{self.metadata.base_url}/csearch/search/search?render=search&platform=pc&q={encoded}&sort=ranking"
