from __future__ import annotations

from .dom_candidates import extract_dom_candidates
from .embedded_data import extract_embedded_data_candidates
from .elevenst import extract_elevenst_candidates
from .json_ld import extract_json_ld_candidates
from .kurly import extract_kurly_candidates
from .lotteon import extract_lotteon_candidates
from .musinsa import extract_musinsa_candidates
from .twenty_nine_cm import extract_twenty_nine_cm_candidates


SITE_SPECIFIC_EXTRACTORS = {
    "29cm": extract_twenty_nine_cm_candidates,
    "elevenst": extract_elevenst_candidates,
    "kurly": extract_kurly_candidates,
    "lotteon": extract_lotteon_candidates,
    "musinsa": extract_musinsa_candidates,
}


def extract_site_specific_candidates(
    html: str,
    metadata=None,
    limit: int = 100,
    query: str | None = None,
):
    if metadata is None:
        return []
    extractor = SITE_SPECIFIC_EXTRACTORS.get(metadata.source)
    if not extractor:
        return []
    return extractor(html, limit=limit, query=query)

__all__ = [
    "extract_dom_candidates",
    "extract_embedded_data_candidates",
    "extract_elevenst_candidates",
    "extract_json_ld_candidates",
    "extract_kurly_candidates",
    "extract_lotteon_candidates",
    "extract_musinsa_candidates",
    "extract_site_specific_candidates",
    "extract_twenty_nine_cm_candidates",
]
