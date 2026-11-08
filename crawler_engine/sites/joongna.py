from __future__ import annotations

import json
import ssl
from urllib.parse import quote
from urllib.error import HTTPError
from urllib.request import Request as UrlRequest
from urllib.request import urlopen

from ..models import CrawlRequest, SourceMetadata


SEARCH_API_URL = "https://search-api.joongna.com/v3/search/all"
PAGE_SIZE = 24


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

    def fetch_search_results(self, request: CrawlRequest, timeout_ms: int = 30000) -> str:
        pages: list[dict[str, object]] = []
        remaining = request.limit
        page = 0
        first_quantity = min(PAGE_SIZE, request.limit)

        while remaining > 0:
            quantity = min(PAGE_SIZE, remaining)
            body = self._search_body(request.query.strip(), page=page, first_quantity=first_quantity, quantity=quantity)
            status, payload = self._post_json(SEARCH_API_URL, body, timeout_ms=timeout_ms)
            items = _items_from_payload(payload)
            pages.append(
                {
                    "page": page,
                    "url": SEARCH_API_URL,
                    "http_status": status,
                    "payload": payload,
                    "item_count": len(items),
                }
            )
            if status != 200 or not _is_success_payload(payload) or not items:
                break
            remaining -= len(items)
            if len(items) < quantity:
                break
            page += 1

        return json.dumps({"pages": pages}, ensure_ascii=False)

    def _search_body(self, query: str, page: int, first_quantity: int, quantity: int) -> dict[str, object]:
        return {
            "osType": "WEB",
            "firstQuantity": first_quantity,
            "quantity": quantity,
            "jnPayYn": "ALL",
            "categoryFilter": [{"categoryDepth": 0, "categorySeq": 0}],
            "priceFilter": {"minPrice": 0, "maxPrice": 999999999},
            "sort": "RECOMMEND_SORT",
            "saleYn": "SALE_N",
            "parcelFeeYn": "ALL",
            "page": page,
            "searchWord": query,
            "adjustSearchKeyword": True,
            "keywordSource": "INPUT_KEYWORD",
            "registPeriod": "ALL",
        }

    def _post_json(
        self,
        url: str,
        body: dict[str, object],
        timeout_ms: int,
    ) -> tuple[int, dict[str, object] | None]:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        request = UrlRequest(
            url,
            data=data,
            method="POST",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
                "Accept": "application/json,text/plain,*/*",
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                "Content-Type": "application/json",
                "Origin": self.metadata.base_url,
                "Referer": f"{self.metadata.base_url}/search/{quote(str(body.get('searchWord') or ''))}",
            },
        )
        context = ssl.create_default_context()
        try:
            with urlopen(request, timeout=max(1, timeout_ms / 1000), context=context) as response:
                return response.status, _decode_json_response(response)
        except HTTPError as exc:
            return exc.code, _decode_json_response(exc)


def _decode_json_response(response) -> dict[str, object] | None:
    raw = response.read()
    charset = response.headers.get_content_charset() or "utf-8"
    text = raw.decode(charset, errors="replace")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _is_success_payload(payload: object) -> bool:
    return isinstance(payload, dict) and isinstance(payload.get("meta"), dict) and payload["meta"].get("code") == 0


def _items_from_payload(payload: object) -> list[object]:
    if not _is_success_payload(payload):
        return []
    data = payload.get("data")
    if not isinstance(data, dict):
        return []
    items = data.get("items")
    return items if isinstance(items, list) else []
