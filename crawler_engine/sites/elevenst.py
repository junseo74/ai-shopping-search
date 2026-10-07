from __future__ import annotations

import json
import ssl
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..models import CrawlRequest, SourceMetadata


class ElevenStSource:
    metadata = SourceMetadata(
        source="elevenst",
        display_name="11st",
        country="KR",
        used_only=False,
        base_url="https://apis.11st.co.kr",
        default_condition="new",
        product_url_hints=("11st.co.kr",),
        product_identity_params=("prdNo", "productNo", "productId", "itemId"),
        canonical_product_url_hints=("11st.co.kr",),
        require_positive_price=True,
    )

    def build_search_url(self, request: CrawlRequest) -> str:
        params = self._search_params(request.query.strip(), page_no=1)
        return f"{self.metadata.base_url}/search/api/tab?{urlencode(params)}"

    def fetch_search_results(self, request: CrawlRequest, timeout_ms: int = 30000) -> str:
        pages: list[dict[str, object]] = []
        for page_no in (1, 2):
            url = f"{self.metadata.base_url}/search/api/tab?{urlencode(self._search_params(request.query.strip(), page_no))}"
            text = self._get(url, timeout_ms=timeout_ms)
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                payload = None
            pages.append({"page_no": page_no, "url": url, "payload": payload})
        return json.dumps({"pages": pages}, ensure_ascii=False)

    def _search_params(self, query: str, page_no: int) -> dict[str, str]:
        return {
            "poc": "mw",
            "tabId": "TOTAL_SEARCH",
            "tier": "A",
            "searchKeyword": query,
            "pageNo": str(page_no),
            "_": str(int(time.time() * 1000)),
        }

    def _get(self, url: str, timeout_ms: int) -> str:
        request = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
                "Accept": "application/json,text/plain,*/*",
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                "Referer": "https://search.11st.co.kr/pc/total-search",
            },
        )
        context = ssl.create_default_context()
        with urlopen(request, timeout=max(1, timeout_ms / 1000), context=context) as response:
            raw = response.read()
            charset = response.headers.get_content_charset() or "utf-8"
            return raw.decode(charset, errors="replace")
