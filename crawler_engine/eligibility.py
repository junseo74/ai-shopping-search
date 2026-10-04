from __future__ import annotations

from urllib.parse import urlparse

from .aggregation import product_identity
from .models import ProductCandidate, SourceMetadata
from .normalize import normalize_text, normalize_url

BAD_NAME_PHRASES = {
    "\uc694\uae08\ud560\uc778(\uc120\ud0dd\uc57d\uc815)",
    "\ub2e8\ub9d0\ud560\uc778(\uacf5\ud1b5\uc9c0\uc6d0)",
    "\ud61c\ud0dd \ucd5c\uc800\uac00",
}


def is_eligible_product_candidate(
    candidate: ProductCandidate,
    metadata: SourceMetadata,
    base_url: str,
) -> bool:
    name = normalize_text(candidate.product_name)
    if not name or name.lower() in BAD_NAME_PHRASES:
        return False
    url = normalize_url(candidate.product_url, base_url)
    if not url:
        return False
    if not product_identity(candidate, metadata, base_url):
        return False
    if not _url_allowed(url, metadata):
        return False
    if metadata.require_positive_price and (candidate.price is None or candidate.price <= 0):
        return False
    return True


def _url_allowed(url: str, metadata: SourceMetadata) -> bool:
    lowered = url.lower()
    if any(hint.lower() in lowered for hint in metadata.excluded_url_hints):
        return False
    if not metadata.allow_ad_products and any(hint.lower() in lowered for hint in metadata.ad_url_hints):
        return False
    if metadata.canonical_product_url_hints:
        return all(hint.lower() in lowered for hint in metadata.canonical_product_url_hints)
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
