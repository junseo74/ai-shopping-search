from __future__ import annotations

from collections.abc import Callable

from .food_details import FoodDetail, apply_food_detail
from .models import ProductCandidate


FoodDetailExtractor = Callable[[str], FoodDetail]


def _extract_kurly_food_detail(html: str) -> FoodDetail:
    from .extractors.kurly import extract_kurly_food_detail

    return extract_kurly_food_detail(html)


DETAIL_EXTRACTORS: dict[str, FoodDetailExtractor] = {
    "kurly": _extract_kurly_food_detail,
}


def get_detail_extractor(source: str) -> FoodDetailExtractor | None:
    return DETAIL_EXTRACTORS.get(source)


def enrich_candidates_with_food_details(
    candidates: list[ProductCandidate],
    source: str,
    fetch_detail_html,
    limit: int,
) -> list[ProductCandidate]:
    extractor = get_detail_extractor(source)
    if extractor is None:
        return candidates

    for candidate in candidates[:limit]:
        product_url = candidate.product_url
        if not product_url:
            continue
        try:
            detail = extractor(fetch_detail_html(product_url))
            apply_food_detail(candidate, detail, source=source)
        except Exception as exc:
            candidate.raw.setdefault("food_detail", {}).update(
                {
                    "source": source,
                    "error": str(exc),
                }
            )
    return candidates
