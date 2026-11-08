from __future__ import annotations

import re
from dataclasses import dataclass, field
from html import unescape
from html.parser import HTMLParser
from typing import Any

from .models import ProductCandidate


GUIDANCE_TEXTS = (
    "상품설명 및 상품이미지 참조",
    "상품설명/상세정보 참조",
    "상품설명 참조",
    "상세정보 참조",
    "이미지 참조",
)
NO_ALLERGEN_TEXTS = ("없음", "해당없음", "해당 없음", "무")


@dataclass
class FoodDetail:
    ingredients: str | None = None
    allergens: list[str] | None = None
    notice_image_urls: list[str] = field(default_factory=list)
    detail_image_urls: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        text = normalize_text(data)
        if text:
            self.parts.append(text)

    def text(self) -> str | None:
        return normalize_text(" ".join(self.parts))


def apply_food_detail(
    candidate: ProductCandidate,
    detail: FoodDetail,
    source: str,
) -> ProductCandidate:
    ingredients = normalize_text(detail.ingredients)
    if ingredients:
        candidate.ingredients = ingredients

    if detail.allergens:
        candidate.allergens = list(detail.allergens)

    raw_payload = {
        "source": source,
        "notice_image_urls": list(detail.notice_image_urls),
        "detail_image_urls": list(detail.detail_image_urls),
        "has_food_notice_images": bool(detail.notice_image_urls or detail.detail_image_urls),
        **detail.raw,
    }
    candidate.raw.setdefault("food_detail", {}).update(raw_payload)
    return candidate


def normalize_text(value: object) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text or None


def is_guidance_text(value: object) -> bool:
    text = normalize_text(value)
    return bool(text and any(guidance in text for guidance in GUIDANCE_TEXTS))


def clean_notice_description(value: object) -> str | None:
    text = normalize_text(value)
    if not text or is_guidance_text(text):
        return None
    return text


def parse_allergens(value: object) -> list[str] | None:
    text = normalize_text(value)
    if not text or text in NO_ALLERGEN_TEXTS:
        return None
    text = re.sub(r"^\s*(?:알레르기|알러지)(?:\s*유발물질)?\s*[:：]\s*", "", text)
    text = re.sub(r"\s*(?:함유|포함)\s*$", "", text)
    parts = [
        normalize_text(part)
        for part in re.split(r"[,/|ㆍ·\n\r]+|\s+및\s+", text)
    ]
    allergens = [part for part in parts if part and part not in NO_ALLERGEN_TEXTS]
    return allergens or None


def html_to_text(value: str) -> str | None:
    parser = TextExtractor()
    parser.feed(unescape(value))
    return parser.text() or normalize_text(re.sub(r"<[^>]+>", " ", unescape(value)))


def html_image_urls(html: str) -> list[str]:
    urls: list[str] = []
    for match in re.finditer(r"<img\b[^>]*\bsrc=[\"'](?P<src>[^\"']+)[\"']", html, re.IGNORECASE):
        url = normalize_text(unescape(match.group("src")))
        if url and not url.startswith("data:") and url not in urls:
            urls.append(url)
    return urls


def walk_json(value: Any):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_json(child)
