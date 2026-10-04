from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urljoin

from .models import CrawledProduct, ProductCandidate, SourceMetadata


NO_NUMERIC_PRICE_MARKERS = (
    "\ubb34\ub8cc\ub098\ub214",
    "\ub098\ub214",
    "\uac00\uaca9\uc81c\uc548",
    "\uac00\uaca9 \uc81c\uc548",
    "\ud611\uc758",
    "\ubb38\uc758",
)
WON_PRICE_PATTERN = re.compile(r"([0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)\s*\uc6d0")
GROUPED_NUMBER_PATTERN = re.compile(r"([0-9]{1,3}(?:,[0-9]{3})+)")
PLAIN_NUMBER_PATTERN = re.compile(r"[0-9]+")


def normalize_text(value: object) -> Optional[str]:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text or None


def normalize_price(value: object, structured: bool = False) -> Optional[int]:
    if structured and isinstance(value, (int, float)):
        if value < 0:
            return None
        return int(value)
    text = normalize_text(value)
    if not text:
        return None
    if any(marker in text for marker in NO_NUMERIC_PRICE_MARKERS):
        return None
    matches = WON_PRICE_PATTERN.findall(text)
    if matches:
        return _digits_to_int(matches[-1])
    fallback = GROUPED_NUMBER_PATTERN.findall(text)
    if fallback:
        return _digits_to_int(fallback[-1])
    if structured and PLAIN_NUMBER_PATTERN.fullmatch(text):
        return int(text)
    return None


def _digits_to_int(value: str) -> Optional[int]:
    digits = re.sub(r"[^0-9]", "", value)
    if not digits:
        return None
    return int(digits)


def normalize_url(value: object, base_url: str) -> Optional[str]:
    text = normalize_text(value)
    if not text:
        return None
    if text.startswith(("data:", "javascript:", "#")):
        return None
    return urljoin(base_url, text)


def normalize_candidate(
    candidate: ProductCandidate,
    metadata: SourceMetadata,
    base_url: str,
) -> Optional[CrawledProduct]:
    name = normalize_text(candidate.product_name)
    if not name:
        return None

    price = candidate.price
    if price is None:
        price = normalize_price(candidate.price_text)
    condition = normalize_text(candidate.condition) or metadata.default_condition
    if condition == "unknown" and metadata.used_only:
        condition = "used"

    return CrawledProduct(
        product_name=name,
        price=price,
        currency=normalize_text(candidate.currency) or "KRW",
        source=metadata.source,
        seller=normalize_text(candidate.seller),
        condition=condition,
        country=normalize_text(candidate.country) or metadata.country,
        product_url=normalize_url(candidate.product_url, base_url),
        image_url=normalize_url(candidate.image_url, base_url),
        description=normalize_text(candidate.description),
    )
