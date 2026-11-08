from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urljoin

from ..models import ProductCandidate


BASE_URL = "https://web.joongna.com"


def extract_joongna_candidates(
    html: str,
    limit: int = 100,
    query: str | None = None,
) -> list[ProductCandidate]:
    payload = _loads_payload(html)
    if payload is None:
        return []

    candidates: list[ProductCandidate] = []
    seen_ids: set[str] = set()
    for item in _product_items(payload):
        product_id = _text(item.get("seq"))
        if not product_id or product_id in seen_ids:
            continue
        candidate = _candidate_from_item(item, product_id)
        if not _is_valid_candidate(candidate):
            continue
        seen_ids.add(product_id)
        candidates.append(candidate)
        if len(candidates) >= limit:
            break
    return candidates


def _loads_payload(value: str) -> Any | None:
    text = value.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _product_items(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    if "pages" in payload:
        items: list[dict[str, Any]] = []
        pages = payload.get("pages")
        if not isinstance(pages, list):
            return []
        for page in pages:
            if not isinstance(page, dict) or page.get("http_status", 200) != 200:
                continue
            items.extend(_product_items(page.get("payload")))
        return items
    if not _is_success_payload(payload):
        return []
    data = payload.get("data")
    if not isinstance(data, dict):
        return []
    items = data.get("items")
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def _is_success_payload(payload: dict[str, Any]) -> bool:
    meta = payload.get("meta")
    return isinstance(meta, dict) and meta.get("code") == 0


def _candidate_from_item(item: dict[str, Any], product_id: str) -> ProductCandidate:
    price = _to_int(item.get("price"))
    state = _to_int(item.get("state"))
    return ProductCandidate(
        product_name=_text(item.get("title")),
        price=price,
        price_text=str(price) if price is not None else None,
        currency="KRW",
        source="joongna",
        seller=None,
        condition="used",
        country="KR",
        product_url=f"{BASE_URL}/product/{product_id}",
        image_url=_absolute_url(_text(item.get("url"))),
        description=None,
        confidence=10,
        raw={
            "product_id": product_id,
            "seq": item.get("seq"),
            "state": state,
            "sale_status": _sale_status(state),
            "sortDate": item.get("sortDate"),
            "mainLocationName": item.get("mainLocationName"),
            "locationNames": item.get("locationNames"),
            "storeSeq": item.get("storeSeq"),
            "userType": item.get("userType"),
            "certifySellerFlag": item.get("certifySellerFlag"),
            "wishCount": item.get("wishCount"),
            "chatCount": item.get("chatCount"),
        },
    )


def _sale_status(state: int | None) -> str | None:
    if state == 0:
        return "available"
    if state == 1:
        return "reserved"
    return None


def _is_valid_candidate(candidate: ProductCandidate) -> bool:
    return bool(
        candidate.raw.get("product_id")
        and candidate.product_name
        and candidate.price is not None
        and candidate.price >= 0
        and candidate.product_url
        and candidate.image_url
    )


def _text(value: object) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text or None


def _to_int(value: object) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        if value < 0:
            return None
        return int(value)
    digits = re.sub(r"[^0-9]", "", str(value))
    return int(digits) if digits else None


def _absolute_url(value: str | None) -> str | None:
    if not value:
        return None
    if value.startswith("//"):
        return f"https:{value}"
    return urljoin(BASE_URL, value)
