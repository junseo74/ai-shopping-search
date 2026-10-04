from __future__ import annotations

import json
from typing import Any, Iterable

from ..models import ProductCandidate
from ..normalize import normalize_price
from ._html import extract_scripts


NAME_KEYS = {"name", "title", "productName", "product_name", "itemName"}
PRICE_KEYS = {"price", "salePrice", "productPrice", "amount"}
URL_KEYS = {"url", "link", "productUrl", "product_url", "itemUrl"}
IMAGE_KEYS = {"image", "imageUrl", "image_url", "thumbnail", "thumbnailUrl"}
SELLER_KEYS = {"seller", "sellerName", "nickname", "storeName"}
DESCRIPTION_KEYS = {"description", "desc", "content"}


def extract_embedded_data_candidates(html: str, limit: int = 100) -> list[ProductCandidate]:
    candidates: list[ProductCandidate] = []
    for script in extract_scripts(html):
        script_type = (script.get("type") or "").lower()
        if "ld+json" in script_type:
            continue
        payload = _parse_script_json(script.get("content") or "")
        if payload is None:
            continue
        for node in _iter_candidate_nodes(payload):
            candidates.append(_candidate_from_mapping(node))
            if len(candidates) >= limit:
                return candidates
    return candidates


def _parse_script_json(content: str) -> Any:
    text = content.strip()
    if not text:
        return None
    if text.startswith(("window.", "self.")) and "=" in text:
        text = text.split("=", 1)[1].strip().rstrip(";")
    if not text.startswith(("{", "[")):
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _iter_candidate_nodes(payload: Any) -> Iterable[dict[str, Any]]:
    if isinstance(payload, list):
        for item in payload:
            yield from _iter_candidate_nodes(item)
    elif isinstance(payload, dict):
        keys = set(payload.keys())
        has_name = bool(keys & NAME_KEYS)
        has_price = bool(keys & PRICE_KEYS)
        has_url_or_image = bool(keys & URL_KEYS) or bool(keys & IMAGE_KEYS)
        if has_name and (has_price or has_url_or_image):
            yield payload
        for value in payload.values():
            if isinstance(value, (dict, list)):
                yield from _iter_candidate_nodes(value)


def _first_value(node: dict[str, Any], keys: set[str]) -> Any:
    for key in keys:
        value = node.get(key)
        if value not in (None, ""):
            return value
    return None


def _candidate_from_mapping(node: dict[str, Any]) -> ProductCandidate:
    seller = _first_value(node, SELLER_KEYS)
    if isinstance(seller, dict):
        seller = seller.get("name") or seller.get("nickname")

    image = _first_value(node, IMAGE_KEYS)
    if isinstance(image, list):
        image = image[0] if image else None
    elif isinstance(image, dict):
        image = image.get("url") or image.get("src")

    price_value = _first_value(node, PRICE_KEYS)
    return ProductCandidate(
        product_name=_first_value(node, NAME_KEYS),
        price=normalize_price(price_value, structured=True),
        price_text=str(price_value) if price_value is not None else None,
        seller=seller,
        product_url=_first_value(node, URL_KEYS),
        image_url=image,
        description=_first_value(node, DESCRIPTION_KEYS),
        raw=node,
    )
