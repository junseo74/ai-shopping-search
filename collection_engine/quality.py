"""Normalize explicit values without inventing provider data or converting FX."""
import math
import re
from decimal import Decimal, InvalidOperation

from pydantic import ValidationError

from backend.models import Product
from .contracts import CollectionError


PRICE = re.compile(r"[+-]?(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)(?:\.[0-9]+)?")


def price_number(value):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise CollectionError("invalid_price")
    if isinstance(value, str):
        value = value.strip()
        if not PRICE.fullmatch(value):
            raise CollectionError("invalid_price")
        value = value.replace(",", "")
    try:
        amount = Decimal(str(value))
        if not amount.is_finite() or amount < 0:
            raise CollectionError("invalid_price")
        number = float(amount)
        if not math.isfinite(number):
            raise CollectionError("invalid_price")
        return number
    except (InvalidOperation, ValueError, OverflowError):
        raise CollectionError("invalid_price") from None


def currency_code(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z]{3}", value.strip()):
        raise CollectionError("invalid_currency")
    return value.strip().upper()


def normalized_product(product):
    # Revalidate at the adapter boundary: model_copy/update and mutable models
    # can carry values that were never checked by Pydantic.
    values = product.model_dump(mode="python", warnings=False)
    name = values.get("product_name")
    if not isinstance(name, str) or not name.strip():
        raise CollectionError("identity_or_name_missing")
    values["product_name"] = name.strip()
    values["price"] = price_number(values.get("price"))
    if values["price"] is None:
        raise CollectionError("invalid_price")
    for field in ("original_price", "shipping_fee"):
        values[field] = price_number(values.get(field))
    values["currency"] = currency_code(values.get("currency"))
    try:
        return Product.model_validate(values)
    except (ValidationError, TypeError):
        raise CollectionError("invalid_product_schema") from None
