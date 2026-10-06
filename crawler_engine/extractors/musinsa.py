from __future__ import annotations

import json
from typing import Any

from ._html import extract_scripts
from ..models import ProductCandidate


PRICE_PRIORITY = ("finalPrice", "couponPrice", "price", "normalPrice")


def extract_musinsa_candidates(
    html: str,
    limit: int = 100,
    query: str | None = None,
) -> list[ProductCandidate]:
    payload = _extract_next_data(html)
    if not payload:
        return []

    candidates: list[ProductCandidate] = []
    for item in _iter_goods_items(payload):
        if not _is_product_item(item):
            continue
        price = _choose_price(item)
        if price is None:
            continue
        candidates.append(_candidate_from_item(item, price))
        if len(candidates) >= limit:
            break
    return candidates


def _extract_next_data(html: str) -> dict[str, Any] | None:
    for script in extract_scripts(html):
        if script.get("id") != "__NEXT_DATA__":
            continue
        content = script.get("content")
        if not content:
            return None
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            return None
        return payload if isinstance(payload, dict) else None
    return None


def _iter_goods_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    queries = (
        payload.get("props", {})
        .get("pageProps", {})
        .get("dehydratedState", {})
        .get("queries", [])
    )
    if not isinstance(queries, list):
        return []

    items: list[dict[str, Any]] = []
    for query in queries:
        if not isinstance(query, dict):
            continue
        state = query.get("state")
        if not isinstance(state, dict):
            continue
        data = state.get("data")
        if not isinstance(data, dict):
            continue
        pages = data.get("pages", [])
        if not isinstance(pages, list):
            continue
        for page in pages:
            if not isinstance(page, dict):
                continue
            page_items = page.get("items", [])
            if not isinstance(page_items, list):
                continue
            items.extend(item for item in page_items if isinstance(item, dict))
    return items


def _is_product_item(item: dict[str, Any]) -> bool:
    return bool(item.get("goodsName") and item.get("goodsLinkUrl") and item.get("thumbnail"))


def _choose_price(item: dict[str, Any]) -> int | None:
    for key in PRICE_PRIORITY:
        price = _positive_int(item.get(key))
        if price is not None:
            return price
    return None


def _positive_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        price = int(value)
        return price if price > 0 else None
    if isinstance(value, str):
        text = value.replace(",", "").strip()
        if text.isdecimal():
            price = int(text)
            return price if price > 0 else None
    return None


def _candidate_from_item(item: dict[str, Any], price: int) -> ProductCandidate:
    return ProductCandidate(
        product_name=str(item.get("goodsName") or ""),
        price=price,
        price_text=str(price),
        currency="KRW",
        source="musinsa",
        seller=_first_text(item.get("brandName"), item.get("brand")),
        condition="new",
        country="KR",
        product_url=str(item.get("goodsLinkUrl") or ""),
        image_url=str(item.get("thumbnail") or ""),
        description=None,
        confidence=10,
        raw={
            "goodsNo": item.get("goodsNo"),
            "brand": item.get("brand"),
            "brandName": item.get("brandName"),
            "normalPrice": item.get("normalPrice"),
            "price": item.get("price"),
            "couponPrice": item.get("couponPrice"),
            "finalPrice": item.get("finalPrice"),
            "finalDiscount": item.get("finalDiscount"),
            "saleRate": item.get("saleRate"),
            "couponSaleRate": item.get("couponSaleRate"),
            "isSoldOut": item.get("isSoldOut"),
            "isAd": item.get("isAd"),
        },
    )


def _first_text(*values: Any) -> str | None:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None
