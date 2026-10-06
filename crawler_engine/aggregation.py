from __future__ import annotations

import re
from html import unescape
from urllib.parse import parse_qs, urlparse, urlunparse

from .models import ProductCandidate, SourceMetadata
from .normalize import normalize_price, normalize_text, normalize_url


PRICE_LIKE_PATTERN = re.compile(r"^(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\s*\uc6d0)?$")
PRICE_LABEL_PATTERN = re.compile(
    r"^(?:\ucd9c\uc2dc\uac00|\ud310\ub9e4\uac00|\uac00\uaca9|\uc815\uac00|\ud560\uc778\uac00|\ucd5c\uc800\uac00|\ud61c\ud0dd\uac00)\s*[:\uFF1A]?\s*"
    r"(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\s*\uc6d0)?$"
)
MALL_COUNT_PATTERN = re.compile(r"^[0-9]+\s*\ubab0$")
RANK_PATTERN = re.compile(r"^[0-9]+\s*\uc704$")
SPEC_LINE_PATTERN = re.compile(
    r"^(?:\ud6c4\uba74|\uc804\uba74|\ud654\uba74|CPU|GPU|RAM|\uba54\ubaa8\ub9ac|\ubc30\ud130\ub9ac|OS)\s*[:\uFF1A]",
    re.IGNORECASE,
)
USED_PATTERN = re.compile(r"(?:\uc911\uace0|S\ub4f1\uae09|A\ub4f1\uae09|\ucd5c\uc0c1\uae09)")
REFURBISHED_PATTERN = re.compile(r"(?:\ub9ac\ud37c|refurbished|renewed)", re.IGNORECASE)
NEW_PATTERN = re.compile(r"(?:\uc0c8\uc0c1\ud488|\ubbf8\uac1c\ubd09|\uc2e0\ud488|\uc790\uae09\uc81c)")

UI_TEXTS = {
    "new \uc0c8\ub85c\uc6cc\uc9c4 \uc0c1\ud488\ube44\uad50 \uae30\ub2a5",
    "\uc744 \uc774\uc6a9\ud574\ubcf4\uc138\uc694.",
    "\ub2eb\uae30",
    "\ud61c\ud0dd \ucd5c\uc800\uac00",
    "\uac00\uaca9\uc815\ubcf4 \ub354\ubcf4\uae30",
    "vs\uc0c1\ud488\ube44\uad50",
}
OPTION_WORDS = {
    "\ud2f0\ud0c0\ub284",
    "\ube14\ub799",
    "\ud654\uc774\ud2b8",
    "\ube14\ub8e8",
    "\uc2e4\ubc84",
    "\uadf8\ub808\uc774",
    "\uadf8\ub9b0",
    "\uc610\ub85c\uc6b0",
    "\ud551\ud06c",
}


def aggregate_candidates(
    candidates: list[ProductCandidate],
    metadata: SourceMetadata,
    base_url: str,
    query: str | None = None,
    include_used: bool = False,
) -> list[ProductCandidate]:
    groups: dict[str, list[ProductCandidate]] = {}
    for index, candidate in enumerate(candidates):
        identity = product_identity(candidate, metadata, base_url) or f"candidate:{index}"
        groups.setdefault(identity, []).append(candidate)

    aggregated: list[ProductCandidate] = []
    for group in groups.values():
        candidate = aggregate_group(group, metadata, base_url, query)
        if candidate and (include_used or candidate.condition != "used"):
            aggregated.append(candidate)
    aggregated = _merge_duplicate_aggregates(aggregated, metadata, base_url, query)
    aggregated.sort(key=lambda item: item.confidence, reverse=True)
    return aggregated


def product_identity(candidate: ProductCandidate, metadata: SourceMetadata, base_url: str) -> str | None:
    url = normalize_url(candidate.product_url, base_url)
    if not url:
        return None
    url = unescape(url)
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    for param in metadata.product_identity_params:
        regex_value = _identity_param_from_url(url, param)
        if regex_value:
            return f"{metadata.source}:{param}:{regex_value}"
        values = query.get(param)
        if values:
            return f"{metadata.source}:{param}:{values[0]}"
    normalized = urlunparse((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", "", ""))
    return f"{metadata.source}:url:{normalized}"


def _identity_param_from_url(url: str, param: str) -> str | None:
    match = re.search(rf"(?:[?&]){re.escape(param)}=([^&#]+)", unescape(url))
    return match.group(1) if match else None


def _merge_duplicate_aggregates(
    candidates: list[ProductCandidate],
    metadata: SourceMetadata,
    base_url: str,
    query: str | None,
) -> list[ProductCandidate]:
    groups: dict[str, list[ProductCandidate]] = {}
    ordered_keys: list[str] = []
    for index, candidate in enumerate(candidates):
        identity = product_identity(candidate, metadata, base_url) or f"candidate:{index}"
        if identity not in groups:
            ordered_keys.append(identity)
        groups.setdefault(identity, []).append(candidate)
    merged: list[ProductCandidate] = []
    for identity in ordered_keys:
        group = groups[identity]
        if len(group) == 1:
            merged.append(group[0])
            continue
        candidate = aggregate_group(group, metadata, base_url, query)
        if candidate:
            merged.append(candidate)
    return merged


def aggregate_group(
    group: list[ProductCandidate],
    metadata: SourceMetadata,
    base_url: str,
    query: str | None,
) -> ProductCandidate | None:
    texts = _group_texts(group)
    name = _choose_representative_name_from_group(group, query)
    if not name:
        return None
    price = _choose_price(group)
    product_url = _choose_product_url(group, metadata, base_url)
    image_url = _choose_image(group)
    condition = infer_condition(texts, metadata.default_condition)
    description = _choose_description(texts, name)
    confidence = max((candidate.confidence for candidate in group), default=0) + _name_score(name, _query_terms(query))
    return ProductCandidate(
        product_name=name,
        price=price,
        currency=group[0].currency if group else "KRW",
        source=metadata.source,
        seller=_first_text(candidate.seller for candidate in group),
        condition=condition,
        country=metadata.country,
        product_url=product_url,
        image_url=image_url,
        description=description,
        confidence=confidence,
        raw={"fragment_count": len(group)},
    )


def choose_representative_name(texts: list[str], query: str | None = None) -> str | None:
    query_terms = _query_terms(query)
    candidates: list[tuple[float, str]] = []
    for text in texts:
        for candidate, _synthetic in _name_candidates_from_text_with_origin(text):
            score = _name_score(candidate, query_terms)
            if score > -50:
                candidates.append((score, candidate))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1][:160]


def _choose_representative_name_from_group(group: list[ProductCandidate], query: str | None) -> str | None:
    query_terms = _query_terms(query)
    direct_candidates: list[tuple[float, str]] = []
    inferred_candidates: list[tuple[float, str]] = []
    for candidate in group:
        product_name = normalize_text(candidate.product_name)
        if product_name:
            for name, _synthetic in _name_candidates_from_text_with_origin(product_name):
                score = _name_score(name, query_terms)
                if score > -50:
                    direct_candidates.append((score, name))
        for value in (candidate.description, candidate.seller):
            text = normalize_text(value)
            if not text:
                continue
            for name, synthetic in _name_candidates_from_text_with_origin(text):
                score = _name_score(name, query_terms)
                if score <= -50:
                    continue
                if synthetic and direct_candidates:
                    score -= 2
                inferred_candidates.append((score, name))
    candidates = [*direct_candidates, *inferred_candidates]
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1][:160]


def infer_condition(texts: list[str], default_condition: str = "unknown") -> str:
    joined = " ".join(texts)
    if USED_PATTERN.search(joined):
        return "used"
    if REFURBISHED_PATTERN.search(joined):
        return "refurbished"
    if NEW_PATTERN.search(joined):
        return "new"
    return default_condition or "unknown"


def _group_texts(group: list[ProductCandidate]) -> list[str]:
    texts: list[str] = []
    for candidate in group:
        for value in (candidate.product_name, candidate.description, candidate.seller):
            text = normalize_text(value)
            if text and text not in texts:
                texts.append(text)
    return texts


def _name_candidates_from_text(text: str) -> list[str]:
    return [candidate for candidate, _synthetic in _name_candidates_from_text_with_origin(text)]


def _name_candidates_from_text_with_origin(text: str) -> list[tuple[str, bool]]:
    has_structured_parts = "/" in text
    raw_parts = [] if has_structured_parts else [text]
    raw_parts.extend(part.strip() for part in re.split(r"\s*/\s*", text) if part.strip())
    parts = [_clean_name(part) for part in raw_parts]
    candidates = [(part, False) for part in parts if part]
    split_parts = [part for part in (parts if has_structured_parts else parts[1:]) if part]
    for start in range(len(split_parts)):
        for end in range(start + 2, min(len(split_parts), start + 6) + 1):
            joined = " ".join(split_parts[start:end])
            cleaned = _clean_name(joined)
            if cleaned:
                candidates.append((cleaned, True))
    return list(dict.fromkeys(candidates))


def _clean_name(value: str) -> str | None:
    text = normalize_text(value)
    if not text:
        return None
    lowered = text.lower()
    if lowered in UI_TEXTS:
        return None
    if _is_price_like(text) or PRICE_LABEL_PATTERN.fullmatch(text) or MALL_COUNT_PATTERN.fullmatch(text) or RANK_PATTERN.fullmatch(text):
        return None
    if SPEC_LINE_PATTERN.search(text):
        return None
    if _is_option_only(text):
        return None
    if len(text) < 3:
        return None
    return text


def _is_price_like(value: str) -> bool:
    text = re.sub(r"\s+", "", value.strip())
    if not text:
        return False
    digits = re.sub(r"[^0-9]", "", text)
    return len(digits) >= 4 and bool(PRICE_LIKE_PATTERN.fullmatch(text))


def _is_option_only(value: str) -> bool:
    lowered = value.lower()
    tokens = re.split(r"\s+|,", lowered)
    has_option_word = any(word.lower() in lowered for word in OPTION_WORDS)
    return has_option_word and len([token for token in tokens if token]) <= 4 and not re.search(r"[0-9]", lowered)


def _name_score(name: str, query_terms: set[str]) -> float:
    lowered = name.lower()
    score = 0.0
    if re.search(r"[\uAC00-\uD7A3A-Za-z]", name):
        score += 2
    if re.search(r"[0-9]", name):
        score += 1
    if re.search(r"(?:GB|TB|\uc790\uae09\uc81c|S[0-9]+|\uc6b8\ud2b8\ub77c|Ultra)", name, re.IGNORECASE):
        score += 2
    if len(re.split(r"\s+", name)) >= 3:
        score += 2
    score += sum(3 for term in query_terms if term in lowered)
    if _is_option_only(name) or SPEC_LINE_PATTERN.search(name):
        score -= 50
    if lowered in UI_TEXTS:
        score -= 100
    return score + min(len(name), 120) / 120


def _query_terms(query: str | None) -> set[str]:
    if not query:
        return set()
    return {term.lower() for term in re.split(r"\s+", query.strip()) if len(term) >= 2}


def _choose_price(group: list[ProductCandidate]) -> int | None:
    prices = [
        price
        for price in (candidate.price if candidate.price is not None else normalize_price(candidate.price_text) for candidate in group)
        if price is not None
    ]
    return min(prices) if prices else None


def _choose_product_url(group: list[ProductCandidate], metadata: SourceMetadata, base_url: str) -> str | None:
    canonical_candidates = []
    fallback_candidates = []
    for candidate in group:
        url = normalize_url(candidate.product_url, base_url)
        if not url:
            continue
        url = unescape(url)
        if metadata.canonical_product_url_hints and all(hint in url for hint in metadata.canonical_product_url_hints):
            canonical_candidates.append(url)
        else:
            fallback_candidates.append(url)
    for url in [*canonical_candidates, *fallback_candidates]:
        if metadata.product_identity_params:
            parsed = urlparse(url)
            query = parse_qs(parsed.query)
            for param in metadata.product_identity_params:
                value = _identity_param_from_url(url, param)
                if value:
                    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", f"{param}={value}", ""))
                if query.get(param):
                    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", f"{param}={query[param][0]}", ""))
        return url
    return None


def _choose_image(group: list[ProductCandidate]) -> str | None:
    for candidate in group:
        image = normalize_text(candidate.image_url)
        if image and not image.startswith(("data:", "javascript:", "#")):
            return image
    return None


def _choose_description(texts: list[str], name: str) -> str | None:
    useful = []
    for text in texts:
        cleaned = _clean_name(text)
        if cleaned and cleaned != name and cleaned not in useful:
            useful.append(cleaned)
        if len(useful) >= 4:
            break
    if not useful:
        return None
    return " / ".join([name, *useful])[:500]


def _first_text(values) -> str | None:
    for value in values:
        text = normalize_text(value)
        if text:
            return text
    return None
