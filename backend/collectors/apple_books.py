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

    def __init__(self):
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
        if not isinstance(limit, int) or not 1 <= limit <= 3:
            raise ValueError("Apple Books verification supports 1 to 3 products only.")
        isbn = re.sub(r"[- ]", "", query or "")
        if not re.fullmatch(r"(?:[0-9]{13}|[0-9]{9}[0-9Xx])", isbn):
            raise ValueError("Use an ISBN-10 or ISBN-13; text search is unsupported.")
        params = {"isbn": isbn, "country": "us", "entity": "ebook", "limit": limit}
        request_url = requests.Request("GET", LOOKUP_URL, params=params).prepare().url
        robots = self._get(ROBOTS_URL)
        if robots.status_code != 200 or "user-agent:" not in robots.text.lower():
            raise RuntimeError(f"Apple robots policy unavailable: HTTP {robots.status_code}; lookup not requested.")
        allowed = robots_allows(robots.text, request_url)
        self.last_audit = {"robots_url": ROBOTS_URL, "robots_status": 200,
                           "user_agent": USER_AGENT, "request_url": request_url,
                           "robots_allowed": allowed, "robots_text": robots.text}
        if not allowed:
            raise RuntimeError("Apple robots.txt disallows the exact lookup URL; request stopped.")
        response = self._get(LOOKUP_URL, params=params)
        self.last_audit["http_status"] = response.status_code
        if response.status_code != 200:
            raise RuntimeError(f"Apple lookup HTTP {response.status_code}; no retry or redirect.")
        body = response.json()
        self.last_response = body
        products, seen = [], set()
        observed = datetime.now(timezone.utc)
        for item in body.get("results", []):
            if item.get("kind") != "ebook" or item.get("trackId") in seen:
                continue
            product = self.to_product(item, observed)
            seen.add(item["trackId"])
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
        return Product(product_name=item["trackName"], price=item["price"],
                       currency=item["currency"], seller=None,
                       platform=PlatformType.SHOPPING_MALL, product_url=url,
                       category=", ".join(item.get("genres", [])) or None,
                       image_url=item.get("artworkUrl100"), condition="unknown",
                       source_url=LOOKUP_URL, source_license=DOCUMENTATION_URL,
                       source_observed_at=observed, data_source=self.metadata.source_name)
