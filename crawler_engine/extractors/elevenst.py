from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urljoin

from ..models import ProductCandidate


BASE_URL = "https://www.11st.co.kr"


def extract_elevenst_candidates(
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
        product_id = _first_text(item, "id", "productNo", "productId", "prdNo", "goodsNo", "itemId")
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
        pass
    match = re.search(r"<pre[^>]*>(.*?)</pre>", text, flags=re.IGNORECASE | re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None
    return None


def _product_items(payload: Any) -> list[dict[str, Any]]:
    arrays: list[tuple[int, list[dict[str, Any]]]] = []
    for _path, value in _walk_json(payload):
        if not isinstance(value, list) or not value:
            continue
        dict_items = [item for item in value if isinstance(item, dict)]
        if not dict_items:
            continue
        score = sum(_product_score(item) for item in dict_items[:10])
        if score < 5:
            continue
        arrays.append((score, dict_items))
    arrays.sort(key=lambda item: (item[0], len(item[1])), reverse=True)
    output: list[dict[str, Any]] = []
    for _score, items in arrays:
        for item in items:
            if _product_score(item) >= 3:
                output.append(item)
    return output


def _walk_json(value: Any, path: str = "$"):
    yield path, value
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _walk_json(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk_json(child, f"{path}[{index}]")


def _product_score(item: dict[str, Any]) -> int:
    keys = {str(key).lower() for key in item.keys()}
    wanted = {
        "id",
        "title",
        "finalprc",
        "selprc",
        "discountprice",
        "linkurl",
        "imageurl",
        "productid",
        "productno",
        "productname",
        "price",
    }
    score = len(keys & wanted)
    if _first_text(item, "title", "productName", "prdName", "goodsName", "itemName", "name"):
        score += 1
    if _price(item) is not None:
        score += 1
    return score


def _candidate_from_item(item: dict[str, Any], product_id: str) -> ProductCandidate:
    price = _price(item)
    product_url = _absolute_url(_first_text(item, "linkUrl", "productUrl", "prdUrl", "goodsUrl", "itemUrl", "url", "link"))
    image_url = _absolute_url(_first_text(item, "imageUrl", "imgUrl", "productImage", "thumbnail", "thumb"))
    title = _first_text(item, "title", "productName", "prdName", "goodsName", "itemName", "name")
    return ProductCandidate(
        product_name=title,
        price=price,
        price_text=str(price) if price is not None else None,
        currency="KRW",
        source="elevenst",
        seller=_first_text(item, "seller", "sellerName", "storeName", "mallName"),
        condition="new",
        country="KR",
        product_url=product_url,
        image_url=image_url,
        description=None,
        confidence=10,
        raw={
            "product_id": product_id,
            "finalPrc": _first_text(item, "finalPrc"),
            "selPrc": _first_text(item, "selPrc"),
            "discountPrice": _first_text(item, "discountPrice"),
            "linkUrl": _first_text(item, "linkUrl"),
        },
    )


def _is_valid_candidate(candidate: ProductCandidate) -> bool:
    return bool(
        candidate.raw.get("product_id")
        and candidate.product_name
        and candidate.price is not None
        and candidate.price > 0
        and candidate.product_url
        and candidate.image_url
    )


def _price(item: dict[str, Any]) -> int | None:
    for key in ("finalPrc", "salePrice", "price", "finalPrice", "displayPrice", "selPrc"):
        value = _first_value(item, key)
        price = _to_int(value)
        if price is not None and price > 0:
            return price
    return None


def _to_int(value: object) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        if value < 0:
            return None
        return int(value)
    text = str(value)
    digits = re.sub(r"[^0-9]", "", text)
    if not digits:
        return None
    return int(digits)


def _first_value(item: dict[str, Any], *keys: str) -> Any:
    lowered = {str(key).lower(): key for key in item.keys()}
    for key in keys:
        real_key = lowered.get(key.lower())
        if real_key is not None and item.get(real_key) not in (None, ""):
            return item.get(real_key)
    return None


def _first_text(item: dict[str, Any], *keys: str) -> str | None:
    value = _first_value(item, *keys)
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text or None


def _absolute_url(value: str | None) -> str | None:
    if not value:
        return None
    if value.startswith("//"):
        return f"https:{value}"
    return urljoin(BASE_URL, value)
