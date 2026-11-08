from __future__ import annotations

import json
import re
from html import unescape
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin

from ..food_details import (
    FoodDetail,
    apply_food_detail,
    clean_notice_description,
    html_image_urls,
    html_to_text,
    normalize_text,
    parse_allergens,
    walk_json,
)
from ..models import ProductCandidate


BASE_URL = "https://www.kurly.com"
PRODUCT_HREF_PATTERN = re.compile(r"(?:^|/)goods/([0-9]+)(?:[/?#]|$)")
PRICE_PATTERN = re.compile(r"([0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)\s*\uc6d0")
NEXT_DATA_PATTERN = re.compile(
    r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(?P<json>.*?)</script>',
    re.DOTALL,
)
INGREDIENT_TITLE_PATTERN = re.compile(r"^INGREDIENT(?:_|$)")


class Node:
    def __init__(self, tag: str, attrs: dict[str, str | None] | None = None, parent: "Node | None" = None) -> None:
        self.tag = tag
        self.attrs = attrs or {}
        self.parent = parent
        self.children: list[Node] = []
        self.text_parts: list[str] = []


class KurlyCardParser(HTMLParser):
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


def extract_kurly_candidates(
    html: str,
    limit: int = 100,
    query: str | None = None,
) -> list[ProductCandidate]:
    parser = KurlyCardParser()
    parser.feed(html)

    candidates: list[ProductCandidate] = []
    seen_ids: set[str] = set()
    for anchor in iter_nodes(parser.root):
        if anchor.tag != "a":
            continue
        href = anchor.attrs.get("href")
        product_id = product_id_from_url(href)
        if not product_id or product_id in seen_ids:
            continue
        seen_ids.add(product_id)
        candidate = _candidate_from_anchor(anchor, product_id, href)
        if not _is_valid_candidate(candidate):
            continue
        candidates.append(candidate)
        if len(candidates) >= limit:
            break
    return candidates


def product_id_from_url(value: str | None) -> str | None:
    if not value:
        return None
    match = PRODUCT_HREF_PATTERN.search(unescape(value))
    return match.group(1) if match else None


def enrich_kurly_candidates_with_details(
    candidates: list[ProductCandidate],
    fetch_detail_html,
) -> list[ProductCandidate]:
    for candidate in candidates:
        product_url = candidate.product_url
        if not product_url:
            continue
        try:
            detail_html = fetch_detail_html(product_url)
            detail = extract_kurly_food_detail(detail_html)
        except Exception as exc:
            candidate.raw.setdefault("food_detail", {}).update(
                {
                    "source": "kurly",
                    "error": str(exc),
                }
            )
            continue
        apply_food_detail(candidate, detail, source="kurly")
    return candidates


def extract_kurly_food_detail(html: str) -> FoodDetail:
    product = _next_data_product(html)
    if not isinstance(product, dict):
        return FoodDetail()

    ingredients = _ingredients_from_content_description(product)
    if not ingredients:
        ingredients = _ingredients_from_product_notice(product)
    allergens = parse_allergens(product.get("allergy"))
    notice_image_urls = _notice_image_urls(product)
    detail_image_urls = _detail_image_urls(product)

    return FoodDetail(
        ingredients=ingredients,
        allergens=allergens,
        notice_image_urls=notice_image_urls,
        detail_image_urls=detail_image_urls,
        raw={
            "allergy_text": normalize_text(product.get("allergy")),
            "product_notice": product.get("productNotice") or [],
        },
    )


def extract_kurly_detail_fields(html: str) -> dict[str, Any]:
    detail = extract_kurly_food_detail(html)
    return {
        "ingredients": detail.ingredients,
        "allergens": detail.allergens,
        "raw": {
            **detail.raw,
            "notice_image_urls": detail.notice_image_urls,
            "detail_image_urls": detail.detail_image_urls,
            "has_food_notice_images": bool(detail.notice_image_urls or detail.detail_image_urls),
        },
    }


def _next_data_product(html: str) -> dict[str, Any] | None:
    match = NEXT_DATA_PATTERN.search(html)
    if not match:
        return None
    payload = json.loads(unescape(match.group("json")))
    product = (
        payload.get("props", {})
        .get("pageProps", {})
        .get("product")
    )
    return product if isinstance(product, dict) else None


def _ingredients_from_content_description(product: dict[str, Any]) -> str | None:
    description = (
        product.get("productDetail", {})
        .get("contentDescription", {})
        .get("description", {})
        .get("description")
    )
    if not isinstance(description, str):
        return None
    text_values: list[str] = []
    try:
        parsed = json.loads(description)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict):
        for node in walk_json(parsed):
            if not isinstance(node, dict):
                continue
            title_type = normalize_text(node.get("titleType"))
            if title_type and INGREDIENT_TITLE_PATTERN.search(title_type):
                text = _text_from_json_module(node.get("main"))
                if text and text not in text_values:
                    text_values.append(text)
    return normalize_text(" / ".join(text_values))


def _ingredients_from_product_notice(product: dict[str, Any]) -> str | None:
    for group in product.get("productNotice") or []:
        if not isinstance(group, dict):
            continue
        for notice in group.get("notices") or []:
            if not isinstance(notice, dict):
                continue
            title = normalize_text(notice.get("title")) or ""
            if "\uc6d0\uc7ac\ub8cc\uba85" not in title:
                continue
            description = clean_notice_description(notice.get("description"))
            if description:
                return description
    return None


def _notice_image_urls(product: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for node in walk_json(product.get("productDetail", {}).get("contentDescription", {})):
        if not isinstance(node, dict):
            continue
        notice_images = node.get("noticeImages")
        if not isinstance(notice_images, list):
            continue
        for item in notice_images:
            if not isinstance(item, dict):
                continue
            image = item.get("image")
            if isinstance(image, dict):
                url = normalize_text(image.get("path"))
                if url and url not in urls:
                    urls.append(url)
    return urls


def _detail_image_urls(product: dict[str, Any]) -> list[str]:
    description = (
        product.get("productDetail", {})
        .get("contentDescription", {})
        .get("description", {})
        .get("description")
    )
    if not isinstance(description, str):
        return []
    return html_image_urls(description)


def _text_from_json_module(value: Any) -> str | None:
    if isinstance(value, dict):
        data = value.get("data")
        if isinstance(data, str):
            return html_to_text(data)
        if isinstance(data, dict):
            return _text_from_json_module(data)
    if isinstance(value, str):
        return html_to_text(value)
    return None


def _candidate_from_anchor(anchor: Node, product_id: str, href: str | None) -> ProductCandidate:
    product_url = urljoin(BASE_URL, unescape(href or ""))
    price_parts = _price_parts(anchor)
    price = _price_from_texts(price_parts["sales_price"]) or _price_from_texts(price_parts["discount_price"])
    name = _product_name(anchor)
    image_url = _product_image(anchor)
    description = _description(anchor, name)
    badges = _badges(anchor)
    return ProductCandidate(
        product_name=name,
        price=price,
        price_text=str(price) if price is not None else None,
        currency="KRW",
        source="kurly",
        seller=None,
        condition="new",
        country="KR",
        product_url=product_url,
        image_url=image_url,
        description=description,
        confidence=10,
        raw={
            "product_id": product_id,
            "original_price": _price_from_texts(price_parts["dimmed_price"]),
            "discount_rate": _percent_from_texts(price_parts["discount_rate"]),
            "review_count": _review_count(anchor),
            "badges": badges,
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


def attr_text(node: Node, *keys: str) -> str | None:
    for key in keys:
        value = normalize_text(node.attrs.get(key))
        if value:
            return value
    return None


def texts_by_class(card: Node, *class_needles: str) -> list[str]:
    values: list[str] = []
    for node in descendants(card):
        if not class_contains(node, *class_needles):
            continue
        text = node_text(node)
        if text and text not in values:
            values.append(text)
    return values


def _price_parts(anchor: Node) -> dict[str, list[str]]:
    return {
        "dimmed_price": texts_by_class(anchor, "dimmed-price"),
        "sales_price": texts_by_class(anchor, "sales-price"),
        "discount_price": texts_by_class(anchor, "discount-price"),
        "discount_rate": texts_by_class(anchor, "discount-rate"),
    }


def _price_from_texts(values: list[str]) -> int | None:
    for value in values:
        match = PRICE_PATTERN.search(value)
        if not match:
            continue
        price = int(re.sub(r"[^0-9]", "", match.group(1)))
        if price > 0:
            return price
    return None


def _percent_from_texts(values: list[str]) -> int | None:
    for value in values:
        match = re.search(r"([0-9]+)\s*%", value)
        if match:
            return int(match.group(1))
    return None


def _product_name(anchor: Node) -> str | None:
    for text in texts_by_class(anchor, "product-name", "goods-name", "name"):
        cleaned = _clean_name(text)
        if cleaned:
            return cleaned
    for image in _image_nodes(anchor):
        if not _is_representative_image_node(image):
            continue
        cleaned = _clean_name(attr_text(image, "alt", "aria-label", "title"))
        if cleaned:
            return cleaned
    return None


def _description(anchor: Node, product_name: str | None) -> str | None:
    for text in texts_by_class(anchor, "desc", "description", "subtitle", "sub-title"):
        cleaned = _clean_description(text, product_name)
        if cleaned:
            return cleaned
    seen_name = False
    for text in _candidate_texts(anchor):
        if product_name and normalize_text(text) == product_name:
            seen_name = True
            continue
        if not seen_name:
            continue
        cleaned = _clean_description(text, product_name)
        if cleaned:
            return cleaned
    return None


def _candidate_texts(anchor: Node) -> list[str]:
    values: list[str] = []
    for node in descendants(anchor):
        text = node_text(node)
        if text and text not in values:
            values.append(text)
    return values


def _clean_name(value: str | None) -> str | None:
    text = normalize_text(value)
    if not text or len(text) < 2 or len(text) > 160:
        return None
    if _is_non_name_text(text):
        return None
    return text


def _clean_description(value: str | None, product_name: str | None) -> str | None:
    text = normalize_text(value)
    if not text or text == product_name or len(text) < 4 or len(text) > 200:
        return None
    if _is_non_name_text(text):
        return None
    return text


def _is_non_name_text(text: str) -> bool:
    if PRICE_PATTERN.search(text):
        return True
    if re.fullmatch(r"[0-9]+\s*%|[0-9,]+|\+?[0-9]+%\s*\ucfe0\ud3f0", text):
        return True
    blocked = (
        "\ub2f4\uae30",
        "\uc7a5\ubc14\uad6c\ub2c8",
        "\uc0db\ubcc4\ubc30\uc1a1",
        "\uccab\uad6c\ub9e4",
        "\ub9ac\ubdf0",
        "Kurly Only",
        "\ucfe0\ud3f0",
        "\ud488\uc808",
    )
    return any(marker in text for marker in blocked)


def _image_nodes(anchor: Node) -> list[Node]:
    return [node for node in descendants(anchor) if node.tag in {"img", "source"}]


def _product_image(anchor: Node) -> str | None:
    for node in _image_nodes(anchor):
        if not _is_representative_image_node(node):
            continue
        image = _image_url_from_node(node)
        return urljoin(BASE_URL, image if not image.startswith("//") else f"https:{image}")
    return None


def _is_representative_image_node(node: Node) -> bool:
    image = _image_url_from_node(node)
    if not image:
        return False
    blocked = ("collection-image", "sticker", "logo", "banner", "badge", "icon", "sprite", "placeholder", "loading")
    combined = f"{image} {class_text(node)} {attr_text(node, 'alt', 'aria-label', 'title') or ''}".lower()
    return not image.startswith("data:") and not any(marker in combined for marker in blocked)


def _image_url_from_node(node: Node) -> str | None:
    for key in ("src", "data-src", "data-original", "data-lazy-src"):
        value = normalize_text(node.attrs.get(key))
        if value:
            return value
    srcset = normalize_text(node.attrs.get("srcset") or node.attrs.get("data-srcset"))
    if srcset:
        return srcset.split(",")[0].strip().split(" ")[0]
    return None


def _review_count(anchor: Node) -> int | None:
    for text in texts_by_class(anchor, "review-count", "review"):
        match = re.search(r"([0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)", text)
        if match:
            return int(re.sub(r"[^0-9]", "", match.group(1)))
    return None


def _badges(anchor: Node) -> list[str]:
    badges: list[str] = []
    for node in descendants(anchor):
        if not class_contains(node, "badge", "label", "tag", "delivery", "shipping"):
            continue
        text = node_text(node)
        if text and len(text) <= 80 and text not in badges:
            badges.append(text)
    return badges[:10]
