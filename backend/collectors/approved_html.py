import os
import re
import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

from .base import BaseCollector, CollectorMetadata

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

try:
    from ..models import PlatformType, Product, ProductCondition
except ImportError:
    from models import PlatformType, Product, ProductCondition


DEFAULT_USER_AGENT = "ai-shopping-search/0.1 (+authorized-product-collection)"


@dataclass(frozen=True)
class HtmlProductFields:
    product_name: Optional[str]
    price: Optional[float]
    shipping_fee: Optional[float]
    seller: Optional[str]
    detail_description: Optional[str]
    image_url: Optional[str]


class HtmlProductParser:
    def parse(self, html: str) -> HtmlProductFields:
        soup = BeautifulSoup(html, "html.parser")
        return HtmlProductFields(
            product_name=self._first_meta(
                soup,
                [("property", "og:title"), ("name", "twitter:title"), ("itemprop", "name")],
            )
            or self._text(soup.select_one("h1")),
            price=self._parse_number(
                self._first_meta(
                    soup,
                    [("property", "product:price:amount"), ("property", "og:price:amount"), ("itemprop", "price")],
                )
            ),
            shipping_fee=self._extract_shipping_fee(soup.get_text(" ", strip=True)),
            seller=self._first_meta(
                soup,
                [("name", "seller"), ("itemprop", "seller"), ("itemprop", "brand")],
            ),
            detail_description=self._first_meta(
                soup,
                [("property", "og:description"), ("name", "description"), ("itemprop", "description")],
            ),
            image_url=self._first_meta(
                soup,
                [("property", "og:image"), ("name", "twitter:image"), ("itemprop", "image")],
            ),
        )

    def _first_meta(self, soup: BeautifulSoup, attrs: list[tuple[str, str]]) -> Optional[str]:
        for key, value in attrs:
            tag = soup.find(attrs={key: value})
            if not tag:
                continue
            content = tag.get("content") or tag.get("href") or tag.get("src")
            if content:
                stripped = content.strip()
                if stripped:
                    return stripped
        return None

    def _text(self, tag) -> Optional[str]:
        if not tag:
            return None
        value = tag.get_text(" ", strip=True)
        return value or None

    def _parse_number(self, value: Optional[str]) -> Optional[float]:
        if not value:
            return None
        normalized = re.sub(r"[^0-9.]", "", value)
        if not normalized:
            return None
        try:
            return float(normalized)
        except ValueError:
            return None

    def _extract_shipping_fee(self, text: str) -> Optional[float]:
        if "\ubb34\ub8cc\ubc30\uc1a1" in text or "\ubc30\uc1a1\ube44 \ubb34\ub8cc" in text:
            return 0.0
        match = re.search(r"\ubc30\uc1a1\ube44\s*([0-9,]+)\s*\uc6d0", text)
        if not match:
            return None
        return self._parse_number(match.group(1))


class ApprovedHtmlProductCollector(BaseCollector):
    metadata = CollectorMetadata(
        source_name="approved_html",
        platform=PlatformType.SHOPPING_MALL,
        requires_api_key=False,
    )

    def __init__(self, parser: Optional[HtmlProductParser] = None) -> None:
        if load_dotenv:
            load_dotenv()
        self.urls = self._load_urls()
        self.parser = parser or HtmlProductParser()
        self.user_agent = os.getenv("APPROVED_HTML_USER_AGENT", DEFAULT_USER_AGENT)
        self.delay_seconds = float(os.getenv("APPROVED_HTML_DELAY_SECONDS", "1.0"))

    def collect(self, query: str | None = None, limit: int = 20) -> list[Product]:
        urls = self._urls_from_query(query) if query else self.urls
        if not urls:
            raise RuntimeError(
                "No approved HTML product URLs configured. Set APPROVED_HTML_PRODUCT_URLS "
                "only for pages where automated collection is explicitly permitted."
            )

        products: list[Product] = []
        for url in urls[:limit]:
            self._ensure_allowed_by_robots(url)
            fields = self.parser.parse(self._fetch(url))
            products.append(
                Product(
                    product_name=fields.product_name or "Untitled approved HTML product",
                    price=fields.price,
                    shipping_fee=fields.shipping_fee,
                    currency="KRW",
                    category=None,
                    seller=fields.seller or "Unknown seller",
                    platform=PlatformType.SHOPPING_MALL,
                    product_url=url,
                    image_url=fields.image_url,
                    condition=ProductCondition.UNKNOWN,
                    region=None,
                    detail_description=fields.detail_description,
                    data_source=self.metadata.source_name,
                )
            )
            time.sleep(self.delay_seconds)
        return products

    def _load_urls(self) -> list[str]:
        raw = os.getenv("APPROVED_HTML_PRODUCT_URLS", "")
        return [url.strip() for url in raw.split(",") if url.strip()]

    def _urls_from_query(self, query: str) -> list[str]:
        return [url.strip() for url in query.split(",") if url.strip()]

    def _fetch(self, url: str) -> str:
        response = requests.get(url, headers={"User-Agent": self.user_agent}, timeout=10)
        response.raise_for_status()
        return response.text

    def _ensure_allowed_by_robots(self, url: str) -> None:
        parsed = urlparse(url)
        robot_parser = RobotFileParser()
        robot_parser.set_url(f"{parsed.scheme}://{parsed.netloc}/robots.txt")
        robot_parser.read()
        if not robot_parser.can_fetch(self.user_agent, url):
            raise RuntimeError(f"robots.txt does not allow fetching this URL: {url}")
