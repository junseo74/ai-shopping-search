from __future__ import annotations

from urllib.parse import quote_plus

from ..models import CrawlRequest, SourceMetadata


class DanawaSource:
    metadata = SourceMetadata(
        source="danawa",
        display_name="Danawa",
        country="KR",
        used_only=False,
        base_url="https://search.danawa.com",
        default_condition="new",
        product_url_hints=("prod.danawa.com/info/", "pcode="),
        product_identity_params=("pcode",),
        canonical_product_url_hints=("prod.danawa.com/info/", "pcode="),
        excluded_url_hints=("dpg.danawa.com/news", "dpg.danawa.com/bbs"),
        ad_url_hints=("ad.danawa.com", "adsmart", "analytics", "linkprice", "11st.co.kr", "coupang.com"),
        allow_ad_products=False,
        require_positive_price=True,
    )

    def build_search_url(self, request: CrawlRequest) -> str:
        encoded = quote_plus(request.query.strip())
        return f"{self.metadata.base_url}/dsearch.php?query={encoded}"
