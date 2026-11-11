"""Small strict parsers shared by documented JSON catalog adapters."""
import math
import re

from .contracts import CollectionError


def object_value(value, optional=False):
    if optional and value is None:
        return {}
    if not isinstance(value, dict):
        raise CollectionError("parsing_error")
    return value


def rows_value(value, limit):
    if not isinstance(value, list):
        raise CollectionError("parsing_error")
    if len(value) > limit:
        raise CollectionError("page_limit_violation")
    if any(not isinstance(row, dict) for row in value):
        raise CollectionError("parsing_error")
    return value


def integer_value(value):
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise CollectionError("parsing_error")
    if isinstance(value, str) and not re.fullmatch(r"[0-9]+", value):
        raise CollectionError("parsing_error")
    try:
        number = int(value)
    except ValueError:
        raise CollectionError("parsing_error") from None
    if number < 0:
        raise CollectionError("parsing_error")
    return number


def provider_id(value):
    if isinstance(value, bool) or not isinstance(value, (int, str)) or not str(value).strip():
        raise CollectionError("parsing_error")
    return str(value)


def page_request(cursor, limit, maximum=None):
    """Keep logical position when the remaining item budget shrinks.

    Legacy numeric cursors mean page at the current size. New multi-item
    cursors also retain the previous size: page:size. Reducing size chooses
    an aligned divisor, avoiding both overlaps and fetching beyond limit.
    """
    try:
        parts = str(cursor or "1").split(":")
        if len(parts) not in (1, 2) or any(not re.fullmatch(r"[0-9]+", part) for part in parts):
            raise ValueError
        page = int(parts[0])
        previous_size = int(parts[1]) if len(parts) == 2 else limit
        if page < 1 or not 1 <= previous_size <= 3:
            raise ValueError
        offset = (page - 1) * previous_size
        size = math.gcd(offset, min(limit, previous_size)) if offset else min(limit, previous_size)
        page = offset // size + 1
    except (ValueError, TypeError, ZeroDivisionError):
        raise CollectionError("invalid_cursor") from None
    if maximum is not None and page > maximum:
        raise CollectionError("pagination_limit")
    return page, size


def next_page_cursor(page, size):
    return str(page + 1) if size == 1 else f"{page + 1}:{size}"
