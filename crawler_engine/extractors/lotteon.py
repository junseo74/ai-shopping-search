from __future__ import annotations

import re
from html import unescape
from html.parser import HTMLParser
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse

from ..models import ProductCandidate


BASE_URL = "https://www.lotteon.com"
CARD_CLASS = "c-product-list__item"
PRODUCT_IMAGE_MARKER = "contents.lotteon.com/itemimage/"
PRODUCT_PATH_PATTERN = re.compile(r"/p/product/(LO[^/?#]+)", re.IGNORECASE)
NUMBER_PATTERN = re.compile(r"(?<![0-9])([0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?![0-9])")


class Node:
    def __init__(self, tag: str, attrs: dict[str, str | None] | None = None, parent: "Node | None" = None) -> None:
        self.tag = tag
        self.attrs = attrs or {}
        self.parent = parent
        self.children: list[Node] = []
        self.text_parts: list[str] = []


class LotteOnParser(HTMLParser):
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


def extract_lotteon_candidates(
    html: str,
    limit: int = 100,
    query: str | None = None,
) -> list[ProductCandidate]:
    parser = LotteOnParser()
    parser.feed(html)

    candidates: list[ProductCandidate] = []
    seen_ids: set[str] = set()
    for card in _cards(parser.root):
        product_url, product_id, sitm_no = _product_link(card)
        if not product_id or product_id in seen_ids:
            continue
        candidate = _candidate_from_card(card, product_id, product_url, sitm_no)
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
    match = PRODUCT_PATH_PATTERN.search(text)
    return match.group(1) if match else None


def sitm_no_from_url(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlparse(urljoin(BASE_URL, unescape(value)))
    values = parse_qs(parsed.query).get("sitmNo")
    return values[0] if values else None


def canonical_product_url(product_id: str) -> str:
    return f"{BASE_URL}/p/product/{product_id}"


def _candidate_from_card(card: Node, product_id: str, product_url: str, sitm_no: str | None) -> ProductCandidate:
    price, original_price, discount_rate, price_text = _price(card)
    brand = _brand(card)
    rating, review_count = _rating_review(card)
    return ProductCandidate(
        product_name=_product_name(card),
        price=price,
        price_text=price_text,
        currency="KRW",
        source="lotteon",
        seller=_seller(card) or brand,
        condition="new",
        country="KR",
        product_url=canonical_product_url(product_id),
        image_url=_image_url_from_card(card),
        description=None,
        confidence=10,
        raw={
            "product_id": product_id,
            "sitm_no": sitm_no,
            "brand": brand,
            "original_price": original_price,
            "discount_rate": discount_rate,
            "rating": rating,
            "review_count": review_count,
            "source_product_url": product_url,
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


def class_list(node: Node) -> list[str]:
    return [part for part in re.split(r"\s+", class_text(node).strip()) if part]


def has_class(node: Node, class_name: str) -> bool:
    return class_name in class_list(node)


def class_contains(node: Node, *needles: str) -> bool:
    lowered = class_text(node).lower()
    return any(needle.lower() in lowered for needle in needles)


def _cards(root: Node) -> list[Node]:
    return [node for node in iter_nodes(root) if node.tag == "li" and has_class(node, CARD_CLASS)]


def _links(card: Node) -> list[Node]:
    return [node for node in descendants(card) if node.tag == "a" and node.attrs.get("href")]


def _product_link(card: Node) -> tuple[str | None, str | None, str | None]:
    for link in _links(card):
        href = link.attrs.get("href")
        product_id = product_id_from_url(href)
        if not product_id:
            continue
        absolute = urljoin(BASE_URL, href or "")
        return absolute, product_id, sitm_no_from_url(absolute)
    return None, None, None


def _product_name(card: Node) -> str | None:
    for node in descendants(card):
        if not class_contains(node, "c-product-title"):
            continue
        text = _clean_name(node_text(node))
        if text:
            return text
    for link in _links(card):
        if not product_id_from_url(link.attrs.get("href")):
            continue
        text = _clean_name(node_text(link))
        if text:
            return text
    return None


def _clean_name(value: object) -> str | None:
    text = normalize_text(value)
    if not text or len(text) < 2 or len(text) > 200:
        return None
    if _is_ui_text(text):
        return None
    if re.fullmatch(r"[0-9,]+\s*\uc6d0?|[0-9]+%|[0-9.]+", text):
        return None
    return text


def _is_ui_text(text: str) -> bool:
    blocked = (
        "\uc88b\uc544\uc694",
        "\ubb34\ub8cc\ubc30\uc1a1",
        "\uc2a4\ud399 \uc815\ubcf4",
        "\ub9ac\ubdf0",
        "\ud3c9\uc810",
        "\uce74\ub4dc \ud560\uc778",
        "AD",
    )
    return any(marker in text for marker in blocked)


def _price(card: Node) -> tuple[int | None, int | None, int | None, str | None]:
    container = _first_node_by_class(card, "c-product-price")
    if not container:
        return None, None, None, None
    original = _price_from_class(container, "c-product-price__real")
    final = _price_from_class(container, "c-product-price__final")
    if final is None:
        final = _last_price_number(node_text(container))
    discount = _discount_from_class(container, "c-product-price__sale")
    return final, original, discount, node_text(container)


def _first_node_by_class(card: Node, needle: str) -> Node | None:
    for node in descendants(card):
        if class_contains(node, needle):
            return node
    return None


def _price_from_class(container: Node, needle: str) -> int | None:
    for node in descendants(container):
        if class_contains(node, needle):
            price = _last_price_number(node_text(node))
            if price is not None:
                return price
    return None


def _discount_from_class(container: Node, needle: str) -> int | None:
    for node in descendants(container):
        if not class_contains(node, needle):
            continue
        text = node_text(node) or ""
        match = re.search(r"([0-9]{1,2})\s*%", text)
        if match:
            return int(match.group(1))
    return None


def _last_price_number(value: object) -> int | None:
    text = normalize_text(value)
    if not text:
        return None
    text = re.sub(r"[0-9]{1,2}\s*%", " ", text)
    numbers = [int(match.replace(",", "")) for match in NUMBER_PATTERN.findall(text)]
    return numbers[-1] if numbers else None


def _image_url_from_card(card: Node) -> str | None:
    blocked = ("logo", "banner", "icon", "badge", "event", "placeholder", "loading")
    for node in descendants(card):
        if node.tag not in {"img", "source"}:
            continue
        image = _image_url(node)
        if not image or PRODUCT_IMAGE_MARKER not in image:
            continue
        combined = f"{image} {class_text(node)} {node.attrs.get('alt') or ''}".lower()
        if any(marker in combined for marker in blocked):
            continue
        return image
    return None


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


def _brand(card: Node) -> str | None:
    for node in descendants(card):
        if not class_contains(node, "brand"):
            continue
        text = normalize_text(node_text(node))
        if text and 1 < len(text) <= 80 and not _is_ui_text(text):
            return text
    return None


def _seller(card: Node) -> str | None:
    for node in descendants(card):
        if not class_contains(node, "seller", "store", "mall", "shop"):
            continue
        text = normalize_text(node_text(node))
        if text and 1 < len(text) <= 80 and not _is_ui_text(text):
            return text
    return None


def _rating_review(card: Node) -> tuple[float | None, int | None]:
    text = node_text(card) or ""
    rating: float | None = None
    review_count: int | None = None
    rating_match = re.search(r"([0-5](?:\.[0-9])?)\s*(?:\uace0\uac1d\ud3c9\uc810|\ud3c9\uc810)", text)
    if rating_match:
        rating = float(rating_match.group(1))
    else:
        rating_match = re.search(r"(?:\uace0\uac1d\ud3c9\uc810|\ud3c9\uc810)\s*([0-5](?:\.[0-9])?)", text)
        if rating_match:
            rating = float(rating_match.group(1))
    review_match = re.search(r"([0-9,]+)\s*(?:\ub9ac\ubdf0|\uac74)", text)
    if review_match:
        review_count = int(review_match.group(1).replace(",", ""))
    return rating, review_count
