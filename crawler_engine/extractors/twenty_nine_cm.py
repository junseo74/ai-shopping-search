from __future__ import annotations

import re
from html import unescape
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin

from ..models import ProductCandidate


BASE_URL = "https://www.29cm.co.kr"
PRODUCT_URL_PATTERN = re.compile(r"product\.29cm\.co\.kr/catalog/([0-9]+)", re.IGNORECASE)
CATALOG_PATH_PATTERN = re.compile(r"/catalog/([0-9]+)(?:[/?#]|$)", re.IGNORECASE)
ITEM_IMAGE_MARKER = "img.29cm.co.kr/item/"
GROUPED_PRICE_PATTERN = re.compile(r"(?<![%0-9])([0-9]{1,3}(?:,[0-9]{3})+)(?!\s*%)")


class Node:
    def __init__(self, tag: str, attrs: dict[str, str | None] | None = None, parent: "Node | None" = None) -> None:
        self.tag = tag
        self.attrs = attrs or {}
        self.parent = parent
        self.children: list[Node] = []
        self.text_parts: list[str] = []


class TwentyNineCmParser(HTMLParser):
    VOID_TAGS = {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Node("document")
        self.current = self.root

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_name = tag.lower()
        node = Node(tag_name, {key.lower(): value for key, value in attrs}, self.current)
        self.current.children.append(node)
        if tag_name not in self.VOID_TAGS:
            self.current = node

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_name = tag.lower()
        self.current.children.append(Node(tag_name, {key.lower(): value for key, value in attrs}, self.current))

    def handle_endtag(self, tag: str) -> None:
        tag_name = tag.lower()
        node = self.current
        while node.parent is not None:
            if node.tag == tag_name:
                self.current = node.parent
                return
            node = node.parent

    def handle_data(self, data: str) -> None:
        text = normalize_text(data)
        if text:
            self.current.text_parts.append(text)


def extract_twenty_nine_cm_candidates(
    html: str,
    limit: int = 100,
    query: str | None = None,
) -> list[ProductCandidate]:
    parser = TwentyNineCmParser()
    parser.feed(html)

    candidates: list[ProductCandidate] = []
    seen_ids: set[str] = set()
    for image in _item_images(parser.root):
        link = _nearest_product_link(image)
        if not link:
            continue
        product_id = product_id_from_url(link.attrs.get("href"))
        if not product_id or product_id in seen_ids:
            continue
        card = _card_container(image, link)
        candidate = _candidate_from_card(card, image, product_id)
        if not _is_valid_candidate(candidate):
            continue
        seen_ids.add(product_id)
        candidates.append(candidate)
        if len(candidates) >= limit:
            break
    return candidates


def product_id_from_url(value: str | None) -> str | None:
    if not value:
        return None
    text = unescape(value)
    match = PRODUCT_URL_PATTERN.search(text) or CATALOG_PATH_PATTERN.search(text)
    return match.group(1) if match else None


def canonical_product_url(product_id: str) -> str:
    return f"https://product.29cm.co.kr/catalog/{product_id}"


def _candidate_from_card(card: Node, image: Node, product_id: str) -> ProductCandidate:
    name = _product_name(card, image)
    price = _price(card)
    image_url = _image_url(image)
    brand = _brand(card, name)
    return ProductCandidate(
        product_name=name,
        price=price,
        price_text=str(price) if price is not None else None,
        currency="KRW",
        source="29cm",
        seller=brand,
        condition="new",
        country="KR",
        product_url=canonical_product_url(product_id),
        image_url=image_url,
        description=None,
        confidence=10,
        raw={
            "product_id": product_id,
            "brand": brand,
            "discount_rate": _discount_rate(card),
        },
    )


def _is_valid_candidate(candidate: ProductCandidate) -> bool:
    return bool(
        candidate.raw.get("product_id")
        and candidate.product_name
        and candidate.price
        and candidate.price > 0
        and candidate.product_url
        and candidate.image_url
    )


def iter_nodes(node: Node):
    yield node
    for child in node.children:
        yield from iter_nodes(child)


def descendants(node: Node):
    for child in node.children:
        yield child
        yield from descendants(child)


def normalize_text(value: object) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text or None


def node_text(node: Node) -> str | None:
    parts = list(node.text_parts)
    for child in node.children:
        text = node_text(child)
        if text:
            parts.append(text)
    return normalize_text(" ".join(parts))


def class_text(node: Node) -> str:
    return node.attrs.get("class") or ""


def class_contains(node: Node, *needles: str) -> bool:
    lowered = class_text(node).lower()
    return any(needle.lower() in lowered for needle in needles)


def texts_by_class(card: Node, *class_needles: str) -> list[str]:
    values: list[str] = []
    for node in descendants(card):
        if not class_contains(node, *class_needles):
            continue
        text = normalize_text(" ".join(node.text_parts)) or node_text(node)
        if text and text not in values:
            values.append(text)
    return values


def _image_url(node: Node) -> str | None:
    for key in ("src", "data-src", "data-original", "data-lazy-src"):
        value = normalize_text(node.attrs.get(key))
        if value:
            return value if value.startswith(("http://", "https://")) else urljoin(BASE_URL, value)
    srcset = normalize_text(node.attrs.get("srcset") or node.attrs.get("data-srcset"))
    if srcset:
        value = srcset.split(",")[0].strip().split(" ")[0]
        return value if value.startswith(("http://", "https://")) else urljoin(BASE_URL, value)
    return None


def _item_images(root: Node) -> list[Node]:
    images: list[Node] = []
    blocked = ("logo", "icon", "banner", "badge", "placeholder", "sprite")
    for node in iter_nodes(root):
        if node.tag not in {"img", "source"}:
            continue
        image = _image_url(node)
        if not image or ITEM_IMAGE_MARKER not in image:
            continue
        combined = f"{image} {class_text(node)} {node.attrs.get('alt') or ''}".lower()
        if any(marker in combined for marker in blocked):
            continue
        images.append(node)
    return images


def _nearest_product_link(node: Node) -> Node | None:
    current: Node | None = node
    while current is not None:
        if current.tag == "a" and product_id_from_url(current.attrs.get("href")):
            return current
        current = current.parent
    return None


def _card_container(image: Node, link: Node) -> Node:
    current: Node | None = link
    best = link
    while current is not None:
        if current.tag == "li":
            return current
        text = node_text(current) or ""
        if len(text) < 2000 and _contains_item_image(current) and _contains_catalog_link(current):
            best = current
        current = current.parent
    return best


def _contains_item_image(node: Node) -> bool:
    return any(child.tag in {"img", "source"} and ITEM_IMAGE_MARKER in (_image_url(child) or "") for child in descendants(node))


def _contains_catalog_link(node: Node) -> bool:
    return any(child.tag == "a" and product_id_from_url(child.attrs.get("href")) for child in descendants(node))


def _product_name(card: Node, image: Node) -> str | None:
    for text in texts_by_class(card, "product-name", "item-name", "goods-name", "name", "title"):
        cleaned = _clean_name(text)
        if cleaned:
            return cleaned
    for value in (image.attrs.get("alt"), image.attrs.get("aria-label"), image.attrs.get("title")):
        cleaned = _clean_name(value)
        if cleaned:
            return cleaned
    return None


def _text_candidates(card: Node) -> list[str]:
    values: list[str] = []
    for node in descendants(card):
        text = normalize_text(" ".join(node.text_parts))
        if text and text not in values:
            values.append(text)
    return values


def _clean_name(value: object) -> str | None:
    text = normalize_text(value)
    if not text or len(text) < 2 or len(text) > 200:
        return None
    if _is_non_name_text(text):
        return None
    return text


def _is_non_name_text(text: str) -> bool:
    if GROUPED_PRICE_PATTERN.search(text):
        return True
    if re.fullmatch(r"[0-9]+\s*%|[0-9.]+|[0-9,]+", text):
        return True
    blocked = (
        "\ubb34\ub8cc\ubc30\uc1a1",
        "\ub9ac\ubdf0",
        "\uc88b\uc544\uc694",
        "\ucfe0\ud3f0",
        "\ub2f4\uae30",
        "\ub7ad\ud0b9",
        "\ud560\uc778",
    )
    return any(marker in text for marker in blocked)


def _price(card: Node) -> int | None:
    candidates: list[int] = []
    for text in _text_candidates(card):
        if "%" in text:
            text = re.sub(r"[0-9]+\s*%", " ", text)
        for match in GROUPED_PRICE_PATTERN.finditer(text):
            value = int(match.group(1).replace(",", ""))
            if value >= 1000:
                candidates.append(value)
    return candidates[-1] if candidates else None


def _discount_rate(card: Node) -> int | None:
    for text in _text_candidates(card):
        match = re.search(r"([0-9]+)\s*%", text)
        if match:
            return int(match.group(1))
    return None


def _brand(card: Node, product_name: str | None) -> str | None:
    for text in _text_candidates(card):
        cleaned = normalize_text(text)
        if not cleaned or cleaned == product_name or _is_non_name_text(cleaned):
            continue
        if len(cleaned) <= 60:
            return cleaned
    return None
