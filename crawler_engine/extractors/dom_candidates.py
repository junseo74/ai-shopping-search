from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Optional

from ..models import ProductCandidate


PRICE_PATTERN = re.compile(
    r"(?:\ubb34\ub8cc\ub098\ub214|\uac00\uaca9\s*\uc81c\uc548|\uac00\uaca9\uc81c\uc548|[0-9][0-9,\s]*\s*\uc6d0)"
)
PRODUCT_URL_PATTERN = re.compile(
    r"(?:/(?:product|products|goods|item|items|article|articles)/|prod\.danawa\.com/info/|[?&]pcode=)",
    re.IGNORECASE,
)
PRICE_TEXT_PATTERN = re.compile(r"^(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\s*\uc6d0)?$")
PRODUCT_ITEM_ID_PATTERN = re.compile(r"^productItem[0-9]+$")
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
NON_NAME_TEXTS = {
    "\uad00\uc2ec",
    "\uad00\uc2ec\uc0c1\ud488",
    "\uc774\ubbf8\uc9c0\ubcf4\uae30",
    "\ub3d9\uc601\uc0c1",
    "\uac00\uaca9\uc815\ubcf4 \ub354\ubcf4\uae30",
    "vs\uc0c1\ud488\ube44\uad50",
}


class LinkBlockParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[dict[str, object]] = []
        self._current: Optional[dict[str, object]] = None
        self._depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key.lower(): value for key, value in attrs}
        if self._current is None and tag.lower() == "a" and attr_map.get("href"):
            self._current = {"href": attr_map.get("href"), "images": [], "text": []}
            self._append_attr_text(self._current, attr_map)
            self._depth = 1
            return
        if self._current is None:
            return
        if tag.lower() == "img":
            src = _first_image_attr(attr_map)
            if src:
                images = self._current["images"]
                assert isinstance(images, list)
                images.append(src)
            self._append_attr_text(self._current, attr_map)
            return
        if tag.lower() not in VOID_TAGS:
            self._depth += 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)

    def handle_data(self, data: str) -> None:
        if self._current is None:
            return
        stripped = data.strip()
        if stripped:
            text = self._current["text"]
            assert isinstance(text, list)
            text.append(stripped)

    def handle_endtag(self, tag: str) -> None:
        if self._current is None:
            return
        self._depth -= 1
        if self._depth <= 0:
            self.blocks.append(self._current)
            self._current = None
            self._depth = 0

    def _append_attr_text(self, block: dict[str, object], attr_map: dict[str, str | None]) -> None:
        text = block["text"]
        assert isinstance(text, list)
        for key in ("aria-label", "title", "alt"):
            value = attr_map.get(key)
            if value:
                text.append(value.strip())


class ElementBlockParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[dict[str, object]] = []
        self._stack: list[dict[str, object]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key.lower(): value for key, value in attrs}
        node: dict[str, object] = {"tag": tag.lower(), "hrefs": [], "images": [], "text": [], "direct_images": []}
        if tag.lower() == "a" and attr_map.get("href"):
            hrefs = node["hrefs"]
            assert isinstance(hrefs, list)
            hrefs.append(attr_map["href"])
            self._append_attr_text(node, attr_map)
        if tag.lower() == "img":
            src = _first_image_attr(attr_map)
            if src:
                images = node["images"]
                direct_images = node["direct_images"]
                assert isinstance(images, list)
                assert isinstance(direct_images, list)
                images.append(src)
                direct_images.append(src)
            self._append_attr_text(node, attr_map)
        self._stack.append(node)
        if tag.lower() in VOID_TAGS:
            self._close_current_node()

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)

    def handle_data(self, data: str) -> None:
        if not self._stack:
            return
        stripped = data.strip()
        if stripped:
            text = self._stack[-1]["text"]
            assert isinstance(text, list)
            text.append(stripped)

    def handle_endtag(self, tag: str) -> None:
        if self._stack:
            self._close_current_node()

    def _close_current_node(self) -> None:
        node = self._stack.pop()
        self._maybe_add_block(node)
        if not self._stack:
            return
        parent = self._stack[-1]
        for key in ("hrefs", "images", "text", "direct_images"):
            parent_values = parent[key]
            node_values = node[key]
            assert isinstance(parent_values, list)
            assert isinstance(node_values, list)
            parent_values.extend(node_values)

    def _maybe_add_block(self, node: dict[str, object]) -> None:
        hrefs = [str(value) for value in node.get("hrefs", []) if _looks_like_product_url(str(value))]
        if not hrefs:
            return
        text = " ".join(str(value) for value in node.get("text", []))
        if not _first_price(text):
            return
        if not node.get("direct_images") and len(hrefs) > 8:
            return
        if len(text) > 2000:
            return
        self.blocks.append(node)

    def _append_attr_text(self, node: dict[str, object], attr_map: dict[str, str | None]) -> None:
        text = node["text"]
        assert isinstance(text, list)
        for key in ("aria-label", "title", "alt"):
            value = attr_map.get(key)
            if value:
                text.append(value.strip())


class ProductItemCardParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[dict[str, object]] = []
        self._current: Optional[dict[str, object]] = None
        self._li_depth = 0
        self._title_depth = 0
        self._prod_name_depth = 0
        self._title_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_name = tag.lower()
        attr_map = {key.lower(): value for key, value in attrs}
        if self._current is None:
            element_id = attr_map.get("id") or ""
            if tag_name == "li" and PRODUCT_ITEM_ID_PATTERN.match(element_id):
                self._current = {"hrefs": [], "images": [], "text": [], "card_id": element_id}
                self._li_depth = 1
                self._append_attr_text(self._current, attr_map)
            return

        class_name = attr_map.get("class") or ""
        if tag_name == "li":
            self._li_depth += 1
        elif self._prod_name_depth > 0 and tag_name not in VOID_TAGS:
            self._prod_name_depth += 1
        elif "prod_name" in class_name and tag_name not in VOID_TAGS:
            self._prod_name_depth = 1
        if self._title_depth > 0 and tag_name not in VOID_TAGS:
            self._title_depth += 1
        if tag_name == "a" and attr_map.get("href"):
            hrefs = self._current["hrefs"]
            assert isinstance(hrefs, list)
            hrefs.append(attr_map["href"])
            self._append_attr_text(self._current, attr_map)
            if "title" in class_name or self._prod_name_depth > 0:
                self._title_depth = 1
                self._title_text = []
        if tag_name == "img":
            src = _first_image_attr(attr_map)
            if src:
                images = self._current["images"]
                assert isinstance(images, list)
                images.append(src)
            self._append_attr_text(self._current, attr_map)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)

    def handle_data(self, data: str) -> None:
        if self._current is None:
            return
        stripped = data.strip()
        if stripped:
            if self._title_depth > 0:
                self._title_text.append(stripped)
                return
            text = self._current["text"]
            assert isinstance(text, list)
            text.append(stripped)

    def handle_endtag(self, tag: str) -> None:
        if self._current is None:
            return
        tag_name = tag.lower()
        if self._title_depth > 0 and tag_name != "li":
            self._title_depth -= 1
            if self._title_depth <= 0:
                title = re.sub(r"\s+", " ", " ".join(self._title_text)).strip()
                if title:
                    text = self._current["text"]
                    assert isinstance(text, list)
                    text.append(title)
                self._title_text = []
        if self._prod_name_depth > 0 and tag_name != "li":
            self._prod_name_depth -= 1
        if tag_name != "li":
            return
        self._li_depth -= 1
        if self._li_depth <= 0:
            self.blocks.append(self._current)
            self._current = None
            self._li_depth = 0
            self._title_depth = 0
            self._prod_name_depth = 0
            self._title_text = []

    def _append_attr_text(self, block: dict[str, object], attr_map: dict[str, str | None]) -> None:
        text = block["text"]
        assert isinstance(text, list)
        for key in ("aria-label", "title", "alt"):
            value = attr_map.get(key)
            if value:
                text.append(value.strip())


def extract_dom_candidates(
    html: str,
    limit: int = 100,
    product_url_hints: tuple[str, ...] = (),
    query: str | None = None,
) -> list[ProductCandidate]:
    candidates: list[ProductCandidate] = []
    card_parser = ProductItemCardParser()
    card_parser.feed(html)
    for block in card_parser.blocks:
        candidate = _candidate_from_element_block(block, product_url_hints, query)
        if candidate:
            candidates.append(candidate)
        if len(candidates) >= limit:
            break

    parser = LinkBlockParser()
    parser.feed(html)
    for block in parser.blocks:
        candidate = _candidate_from_link_block(block, product_url_hints, query)
        if candidate:
            candidates.append(candidate)
        if len(candidates) >= limit:
            break
    if len(candidates) < limit:
        block_parser = ElementBlockParser()
        block_parser.feed(html)
        for block in block_parser.blocks:
            candidate = _candidate_from_element_block(block, product_url_hints, query)
            if candidate:
                candidates.append(candidate)
            if len(candidates) >= limit:
                break
    candidates = _dedupe_candidates(candidates)
    candidates.sort(key=lambda candidate: candidate.confidence, reverse=True)
    return candidates[:limit]


def count_links(html: str) -> int:
    parser = LinkBlockParser()
    parser.feed(html)
    return len(parser.blocks)


def count_product_like_links(html: str, product_url_hints: tuple[str, ...] = ()) -> int:
    parser = LinkBlockParser()
    parser.feed(html)
    return sum(1 for block in parser.blocks if _looks_like_product_url(str(block.get("href") or ""), product_url_hints))


def _looks_like_product_url(value: str, product_url_hints: tuple[str, ...] = ()) -> bool:
    if not value:
        return False
    if product_url_hints and any(hint in value for hint in product_url_hints):
        return True
    return bool(PRODUCT_URL_PATTERN.search(value))


def _candidate_from_link_block(
    block: dict[str, object],
    product_url_hints: tuple[str, ...] = (),
    query: str | None = None,
) -> Optional[ProductCandidate]:
    href = str(block.get("href") or "")
    if not _looks_like_product_url(href, product_url_hints):
        return None
    text_parts = [str(value) for value in block.get("text", [])]
    text = " ".join(text_parts)
    price_text = _first_price(text)
    if not price_text:
        return None
    name = _guess_name(text_parts, price_text, query)
    if not name:
        return None
    images = block.get("images", [])
    image = _first_valid_image(images if isinstance(images, list) else [])
    confidence = _score_candidate(str(block.get("href") or ""), name, price_text, bool(image), text, product_url_hints)
    if confidence < 3:
        return None
    return ProductCandidate(
        product_name=name,
        price_text=price_text,
        product_url=href,
        image_url=str(image) if image else None,
        description=_build_description(text_parts, name, price_text),
        confidence=confidence,
    )


def _candidate_from_element_block(
    block: dict[str, object],
    product_url_hints: tuple[str, ...] = (),
    query: str | None = None,
) -> Optional[ProductCandidate]:
    hrefs = [str(value) for value in block.get("hrefs", []) if _looks_like_product_url(str(value), product_url_hints)]
    text_parts = [str(value) for value in block.get("text", [])]
    text = " ".join(text_parts)
    price_text = _first_price(text)
    if not hrefs or not price_text:
        return None
    images = block.get("images", [])
    image = _first_valid_image(images if isinstance(images, list) else [])
    name = _guess_name(text_parts, price_text, query)
    if not name:
        return None
    confidence = _score_candidate(hrefs[0], name, price_text, bool(image), text, product_url_hints)
    if confidence < 3:
        return None
    return ProductCandidate(
        product_name=name,
        price_text=price_text,
        product_url=hrefs[0],
        image_url=str(image) if image else None,
        description=_build_description(text_parts, name, price_text),
        confidence=confidence,
    )


def _first_price(text: str) -> Optional[str]:
    matches = PRICE_PATTERN.findall(text)
    return matches[-1].strip() if matches else None


def _guess_name(text_parts: list[str], price_text: str, query: str | None = None) -> Optional[str]:
    candidates: list[tuple[float, str]] = []
    query_terms = _query_terms(query)
    for part in text_parts:
        parts = [part]
        if price_text in part:
            before_price = part.split(price_text, 1)[0].strip()
            parts = [before_price] if before_price else []
        for item in parts:
            cleaned_part = _clean_name_text(item)
            if not cleaned_part:
                continue
            candidates.append((_name_score(cleaned_part, query_terms), cleaned_part))
    if not candidates:
        return None
    candidates.sort(key=lambda candidate: candidate[0], reverse=True)
    return candidates[0][1][:160]


def _score_candidate(
    url: str,
    name: Optional[str],
    price_text: Optional[str],
    has_image: bool,
    text: str,
    product_url_hints: tuple[str, ...],
) -> float:
    score = 0.0
    if _looks_like_product_url(url, product_url_hints):
        score += 2
    if price_text:
        score += 2
    if has_image:
        score += 1
    if name and 4 <= len(name) <= 160:
        score += 1
    if 8 <= len(text) <= 2000:
        score += 1
    if product_url_hints and any(hint in url for hint in product_url_hints):
        score += 1
    return score


def _first_image_attr(attr_map: dict[str, str | None]) -> Optional[str]:
    for key in ("src", "data-src", "data-original", "data-lazy-src"):
        value = attr_map.get(key)
        if value and _is_valid_image(value):
            return value.strip()
    for key in ("srcset", "data-srcset"):
        value = attr_map.get(key)
        srcset = _first_srcset_url(value)
        if srcset and _is_valid_image(srcset):
            return srcset
    return None


def _first_valid_image(values: list[object]) -> Optional[str]:
    for value in values:
        text = str(value).strip()
        if _is_valid_image(text):
            return text
    return None


def _is_valid_image(value: str) -> bool:
    lowered = value.lower()
    return bool(value) and not lowered.startswith(("data:", "javascript:", "#")) and "nodata/img/noimg" not in lowered


def _first_srcset_url(value: str | None) -> Optional[str]:
    if not value:
        return None
    first = value.split(",", 1)[0].strip()
    return first.split()[0] if first else None


def _is_price_like(value: str) -> bool:
    text = re.sub(r"\s+", "", value.strip())
    if not text:
        return False
    if PRICE_PATTERN.fullmatch(value.strip()):
        return True
    digits = re.sub(r"[^0-9]", "", text)
    return len(digits) >= 4 and bool(PRICE_TEXT_PATTERN.fullmatch(text))


def _clean_name_text(value: str) -> Optional[str]:
    text = re.sub(r"\s+", " ", value).strip()
    if not text:
        return None
    lowered = text.lower()
    if lowered in NON_NAME_TEXTS or _is_price_like(text):
        return None
    if len(text) < 2:
        return None
    return text


def _query_terms(query: str | None) -> set[str]:
    if not query:
        return set()
    return {term.lower() for term in re.split(r"\s+", query.strip()) if len(term) >= 2}


def _name_score(name: str, query_terms: set[str]) -> float:
    lowered = name.lower()
    score = 0.0
    if 4 <= len(name) <= 120:
        score += 3
    if re.search(r"[A-Za-z\uAC00-\uD7A3]", name):
        score += 2
    if query_terms:
        score += sum(2 for term in query_terms if term in lowered)
    if _is_price_like(name):
        score -= 100
    return score + min(len(name), 80) / 80


def _build_description(text_parts: list[str], name: Optional[str], price_text: Optional[str]) -> Optional[str]:
    useful: list[str] = []
    for part in text_parts:
        cleaned = _clean_name_text(part)
        if not cleaned or cleaned in useful:
            continue
        if price_text and price_text in cleaned:
            cleaned = cleaned.split(price_text, 1)[0].strip()
        cleaned = _clean_name_text(cleaned)
        if cleaned and cleaned not in useful:
            useful.append(cleaned)
        if len(useful) >= 4:
            break
    if name and name not in useful:
        useful.insert(0, name)
    if not useful:
        return None
    description = " / ".join(useful)
    return description[:500]


def _dedupe_candidates(candidates: list[ProductCandidate]) -> list[ProductCandidate]:
    seen: set[tuple[str | None, str | None]] = set()
    unique: list[ProductCandidate] = []
    for candidate in candidates:
        key = (candidate.product_url, candidate.price_text)
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return unique
