from __future__ import annotations

from urllib.parse import urlparse

from .models import CrawledProduct


def is_valid_url(value: str | None) -> bool:
    if value is None:
        return True
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def is_valid_product(product: CrawledProduct, max_price: int | None = None) -> bool:
    if not product.product_name.strip():
        return False
    if product.price is not None and product.price < 0:
        return False
    if max_price is not None and product.price is not None and product.price > max_price:
        return False
    if not is_valid_url(product.product_url):
        return False
    if not is_valid_url(product.image_url):
        return False
    return True


def dedupe_products(products: list[CrawledProduct]) -> list[CrawledProduct]:
    seen: set[tuple[str, str, int | None]] = set()
    unique: list[CrawledProduct] = []
    for product in products:
        key = (
            product.source,
            product.product_url or product.product_name.lower(),
            product.price,
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(product)
    return unique
