"""Small, on-demand ISBN lookups through Apple's documented public API.

Text search is deliberately unsupported: /search* is disallowed by robots.txt.
This is not a bulk catalog exporter or a license for unrestricted data reuse.
"""
import re
import time
from datetime import datetime, timezone
from urllib.parse import urlsplit

import requests

from .base import BaseCollector, CollectorMetadata
from collection_engine.contracts import CollectionError
from collection_engine.responses import object_value, rows_value, provider_id
from collection_engine.quality import price_number, currency_code
try:
    from ..models import PlatformType, Product
except ImportError:
    from models import PlatformType, Product


USER_AGENT = "AIShoppingSearchIntegration/1.0"
LOOKUP_URL = "https://itunes.apple.com/lookup"
ROBOTS_URL = "https://itunes.apple.com/robots.txt"
DOCUMENTATION_URL = "https://performance-partners.apple.com/search-api"


def robots_allows(text: str, url: str, user_agent: str = USER_AGENT) -> bool:
    """Match robots groups and wildcard rules for these ASCII API URLs.

    Merge equally specific groups, prefer longest path rule, allow on ties.
    This helper is not intended as a general internationalized URL crawler.
    """
    groups = []
    agents, rules = [], []
    in_rules = False
    for line in text.splitlines() + ["User-agent: __end__"]:
        line = line.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        key, value = (part.strip() for part in line.split(":", 1))
        key = key.lower()
        if key == "user-agent":
            if in_rules:
                groups.append((agents, rules))
                agents, rules, in_rules = [], [], False
            agents.append(value.lower())
        elif key in ("allow", "disallow") and agents:
            in_rules = True
            if value:
                rules.append((key, value))
    matching = []
    for agents, rules in groups:
        scores = [0 if agent == "*" else len(agent) for agent in agents
                  if agent == "*" or agent in user_agent.lower()]
        if scores:
            matching.append((max(scores), rules))
    if not matching:
        return True
    specificity = max(score for score, _ in matching)
    parsed = urlsplit(url)
    target = parsed.path + ("?" + parsed.query if parsed.query else "")
    matches = []
    for score, rules in matching:
        if score != specificity:
            continue
        for directive, pattern in rules:
            anchored = pattern.endswith("$")
            body = pattern[:-1] if anchored else pattern
            expression = "^" + ".*".join(re.escape(part) for part in body.split("*"))
            if anchored:
                expression += "$"
            if re.match(expression, target):
                matches.append((len(body.replace("*", "")), directive == "allow"))
    return max(matches, default=(0, True))[1]


class AppleBooksLookupCollector(BaseCollector):
    metadata = CollectorMetadata("apple_books_lookup", PlatformType.SHOPPING_MALL)

    def __init__(self, transport=None):
        self.transport = transport
        self.last_response = None
        self.last_audit = None
        self._last_request_at = 0.0

    def _get(self, url, **kwargs):
        remaining = 3.1 - (time.monotonic() - self._last_request_at)
        if remaining > 0:
            time.sleep(remaining)
        self._last_request_at = time.monotonic()
        return requests.get(url, headers={"User-Agent": USER_AGENT},
                            timeout=20, allow_redirects=False, **kwargs)

    def collect(self, query=None, limit=3):
        self.last_response = None
        self.last_audit = None
        if type(limit) is not int or not 1 <= limit <= 3:
            raise ValueError("Apple Books verification supports 1 to 3 products only.")
        isbn = re.sub(r"[- ]", "", query or "")
        if not re.fullmatch(r"(?:[0-9]{13}|[0-9]{9}[0-9Xx])", isbn):
            raise ValueError("Use an ISBN-10 or ISBN-13; text search is unsupported.")
        params = {"isbn": isbn, "country": "us", "entity": "ebook", "limit": limit}
        request_url = requests.Request("GET", LOOKUP_URL, params=params).prepare().url
        if self.transport is not None:
            robots_text = self.transport.get_text(ROBOTS_URL, headers={"User-Agent": USER_AGENT})
            robots_status = 200
        else:
            robots = self._get(ROBOTS_URL)
            try:
                robots_text, robots_status = robots.text, robots.status_code
            finally:
                robots.close()
        if robots_status != 200 or "user-agent:" not in robots_text.lower():
            if self.transport is not None:
                raise CollectionError("robots_policy_unavailable")
            raise RuntimeError(f"Apple robots policy unavailable: HTTP {robots_status}; lookup not requested.")
        allowed = robots_allows(robots_text, request_url)
        self.last_audit = {"robots_url": ROBOTS_URL, "robots_status": 200,
                           "user_agent": USER_AGENT, "request_url": request_url,
                           "robots_allowed": allowed, "robots_text": robots_text}
        if not allowed:
            if self.transport is not None:
                raise CollectionError("robots_disallowed")
            raise RuntimeError("Apple robots.txt disallows the exact lookup URL; request stopped.")
        if self.transport is not None:
            body = self.transport.get_json(LOOKUP_URL, params=params, headers={"User-Agent": USER_AGENT})
            self.last_audit["http_status"] = 200
        else:
            response = self._get(LOOKUP_URL, params=params)
            try:
                self.last_audit["http_status"] = response.status_code
                if response.status_code != 200:
                    raise RuntimeError(f"Apple lookup HTTP {response.status_code}; no retry or redirect.")
                try:
                    body = response.json()
                except ValueError:
                    raise CollectionError("parsing_error") from None
            finally:
                response.close()
        body = object_value(body)
        rows = rows_value(body.get("results"), 200)
        self.last_response = body
        products, seen = [], set()
        observed = datetime.now(timezone.utc)
        for item in rows:
            if item.get("kind") != "ebook":
                continue
            identity = provider_id(item.get("trackId"))
            if identity in seen:
                continue
            product = self.to_product(item, observed)
            seen.add(identity)
            products.append(product)
            if len(products) == limit:
                break
        return products

    def to_product(self, item, observed=None):
        url = item.get("trackViewUrl")
        parsed = urlsplit(url or "")
        if parsed.scheme != "https" or parsed.hostname != "books.apple.com":
            raise ValueError("Apple Books result lacks an official HTTPS product URL.")
        if not item.get("trackName") or item.get("price") is None or not item.get("currency"):
            raise ValueError("Apple Books result lacks name, price or currency.")
        return Product(product_name=item["trackName"], price=price_number(item["price"]),
                       currency=currency_code(item["currency"]), seller=None,
                       platform=PlatformType.SHOPPING_MALL, product_url=url,
                       category=", ".join(item.get("genres", [])) or None,
                       image_url=item.get("artworkUrl100"), condition="unknown",
                       source_url=LOOKUP_URL, source_license=DOCUMENTATION_URL,
                       source_observed_at=observed, data_source=self.metadata.source_name)
