from __future__ import annotations

from urllib.parse import quote

from ..models import CrawlRequest, SourceMetadata


class JoongnaSource:
    metadata = SourceMetadata(
        source="joongna",
        display_name="Joonggonara",
        country="KR",
        used_only=True,
        base_url="https://web.joongna.com",
        default_condition="used",
        product_url_hints=("/product/",),
    )

    def build_search_url(self, request: CrawlRequest) -> str:
        encoded = quote(request.query.strip())
        return f"{self.metadata.base_url}/search/{encoded}"
