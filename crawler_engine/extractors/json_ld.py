from __future__ import annotations

import json
from typing import Any, Iterable

from ..models import ProductCandidate
from ..normalize import normalize_price
from ._html import extract_scripts


def extract_json_ld_candidates(html: str) -> list[ProductCandidate]:
    candidates: list[ProductCandidate] = []
    for script in extract_scripts(html):
        script_type = (script.get("type") or "").lower()
        if "ld+json" not in script_type:
            continue
        content = script.get("content") or ""
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            continue
        for node in _iter_product_nodes(payload):
            candidates.append(_candidate_from_product_node(node))
    return candidates


def _iter_product_nodes(payload: Any) -> Iterable[dict[str, Any]]:
    if isinstance(payload, list):
        for item in payload:
            yield from _iter_product_nodes(item)
    elif isinstance(payload, dict):
        node_type = payload.get("@type") or payload.get("type")
        if isinstance(node_type, list):
            types = {str(value).lower() for value in node_type}
        else:
            types = {str(node_type).lower()}
        if "product" in types:
            yield payload
        graph = payload.get("@graph")
        if graph is not None:
            yield from _iter_product_nodes(graph)


def _candidate_from_product_node(node: dict[str, Any]) -> ProductCandidate:
    offer = node.get("offers")
    if isinstance(offer, list):
        offer = offer[0] if offer else {}
    if not isinstance(offer, dict):
        offer = {}

    seller = offer.get("seller") or node.get("seller") or node.get("brand")
    if isinstance(seller, dict):
        seller = seller.get("name")

    image = node.get("image")
    if isinstance(image, list):
        image = image[0] if image else None
    elif isinstance(image, dict):
        image = image.get("url")

    price_value = offer.get("price") or offer.get("lowPrice") or node.get("price")
    return ProductCandidate(
        product_name=node.get("name"),
        price=normalize_price(price_value, structured=True),
        price_text=str(price_value) if price_value is not None else None,
        currency=offer.get("priceCurrency") or node.get("priceCurrency") or "KRW",
        seller=seller,
        product_url=offer.get("url") or node.get("url"),
        image_url=image,
        description=node.get("description"),
        raw=node,
    )
