import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
import yaml
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
DEFAULT_SELECTOR_CONFIG_PATH = Path(__file__).with_name("approved_html_selectors.yml")
MAX_LIST_PRODUCTS = 20


@dataclass(frozen=True)
class HtmlProductFields:
    product_name: Optional[str]
    price: Optional[float]
    shipping_fee: Optional[float]
    seller: Optional[str]
    detail_description: Optional[str]
    image_url: Optional[str]


@dataclass(frozen=True)
class HtmlListSiteConfig:
    name: str
    domains: tuple[str, ...]
    selectors: dict[str, str]
    attributes: dict[str, str]
    default_seller: Optional[str] = None
    permission_note: Optional[str] = None
    permission_reference: Optional[str] = None

    @classmethod
    def from_mapping(cls, raw: dict[str, Any]) -> "HtmlListSiteConfig":
        permission = raw.get("permission") or {}
        if permission.get("approved") is not True:
            raise ValueError(f"HTML selector config for {raw.get('name', '<unnamed>')} is not explicitly approved.")

        selectors = raw.get("selectors") or {}
        required = ["product_card", "product_name", "price", "product_url"]
        missing = [field for field in required if not selectors.get(field)]
        if missing:
            raise ValueError(f"HTML selector config for {raw.get('name', '<unnamed>')} is missing: {', '.join(missing)}")

        domains = tuple(str(domain).lower().strip() for domain in raw.get("domains", []) if str(domain).strip())
        if not domains:
            raise ValueError(f"HTML selector config for {raw.get('name', '<unnamed>')} must include domains.")

        if not (permission.get("note") or permission.get("reference")):
            raise ValueError(
                f"HTML selector config for {raw.get('name', '<unnamed>')} must document the explicit permission."
            )

        return cls(
            name=str(raw.get("name") or domains[0]),
            domains=domains,
            selectors={str(key): str(value) for key, value in selectors.items() if value},
            attributes={str(key): str(value) for key, value in (raw.get("attributes") or {}).items() if value},
            default_seller=raw.get("default_seller"),
            permission_note=permission.get("note"),
            permission_reference=permission.get("reference"),
        )

    def matches(self, url: str) -> bool:
        hostname = (urlparse(url).hostname or "").lower()
        return any(hostname == domain or hostname.endswith(f".{domain}") for domain in self.domains)


@dataclass(frozen=True)
class _ListProductFields:
    product_name: Optional[str]
    price: Optional[float]
    shipping_fee: Optional[float]
    seller: Optional[str]
    detail_description: Optional[str]
    product_url: Optional[str]
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


class HtmlProductListParser:
    def parse(self, html: str, source_url: str, site_config: HtmlListSiteConfig, limit: int) -> list[Product]:
        soup = BeautifulSoup(html, "html.parser")
        products: list[Product] = []
        seen_urls: set[str] = set()

        for card in soup.select(site_config.selectors["product_card"]):
            fields = self._extract_card_fields(card, source_url, site_config)
            if not fields.product_name or fields.price is None or not fields.seller:
                continue

            product_url = fields.product_url
            if not product_url or product_url in seen_urls:
                continue

            seen_urls.add(product_url)
            products.append(
                Product(
                    product_name=fields.product_name,
                    price=fields.price,
                    shipping_fee=fields.shipping_fee,
                    currency="KRW",
                    category=None,
                    seller=fields.seller,
                    platform=PlatformType.SHOPPING_MALL,
                    product_url=product_url,
                    image_url=fields.image_url,
                    condition=ProductCondition.NEW,
                    region=None,
                    detail_description=fields.detail_description,
                    source_url=source_url,
                    data_source="approved_html",
                )
            )
            if len(products) >= limit:
                break

        return products

    def _extract_card_fields(self, card, source_url: str, site_config: HtmlListSiteConfig) -> _ListProductFields:
        product_url = self._absolute_url(
            self._field_value(card, site_config, "product_url", default_attr="href"),
            source_url,
        )
        image_url = self._absolute_url(
            self._field_value(card, site_config, "image_url", default_attr="src"),
            source_url,
        )

        return _ListProductFields(
            product_name=self._field_text(card, site_config, "product_name"),
            price=self._parse_number(self._field_text(card, site_config, "price")),
            shipping_fee=self._parse_shipping_fee(self._field_text(card, site_config, "shipping_fee")),
            seller=self._field_text(card, site_config, "seller") or site_config.default_seller,
            detail_description=self._field_text(card, site_config, "detail_description"),
            product_url=product_url,
            image_url=image_url,
        )

    def _field_text(self, card, site_config: HtmlListSiteConfig, field: str) -> Optional[str]:
        return self._field_value(card, site_config, field)

    def _field_value(
        self,
        card,
        site_config: HtmlListSiteConfig,
        field: str,
        default_attr: Optional[str] = None,
    ) -> Optional[str]:
        selector = site_config.selectors.get(field)
        if not selector:
            return None
        tag = card.select_one(selector)
        if not tag:
            return None
        attr = site_config.attributes.get(field) or default_attr
        value = tag.get(attr) if attr else tag.get_text(" ", strip=True)
        if value is None:
            return None
        value = str(value).strip()
        return value or None

    def _absolute_url(self, value: Optional[str], source_url: str) -> Optional[str]:
        if not value:
            return None
        return urljoin(source_url, value)

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

    def _parse_shipping_fee(self, value: Optional[str]) -> Optional[float]:
        if not value:
            return None
        if "\ubb34\ub8cc" in value or "free" in value.lower():
            return 0.0
        return self._parse_number(value)


class ApprovedHtmlProductCollector(BaseCollector):
    metadata = CollectorMetadata(
        source_name="approved_html",
        platform=PlatformType.SHOPPING_MALL,
        requires_api_key=False,
    )

    def __init__(
        self,
        parser: Optional[HtmlProductParser] = None,
        list_parser: Optional[HtmlProductListParser] = None,
        selector_config_path: Optional[str | Path] = None,
    ) -> None:
        if load_dotenv:
            load_dotenv()
        self.urls = self._load_urls()
        self.parser = parser or HtmlProductParser()
        self.list_parser = list_parser or HtmlProductListParser()
        self.user_agent = os.getenv("APPROVED_HTML_USER_AGENT", DEFAULT_USER_AGENT)
        self.delay_seconds = float(os.getenv("APPROVED_HTML_DELAY_SECONDS", "1.0"))
        self.timeout_seconds = float(os.getenv("APPROVED_HTML_TIMEOUT_SECONDS", "10.0"))
        self.selector_config_path = Path(
            selector_config_path
            or os.getenv("APPROVED_HTML_SELECTOR_CONFIG", str(DEFAULT_SELECTOR_CONFIG_PATH))
        )
        self.site_configs = self._load_site_configs()

    def collect(self, query: str | None = None, limit: int = 20) -> list[Product]:
        if query:
            raise ValueError("Approved HTML collection uses APPROVED_HTML_LIST_URLS only; do not pass arbitrary URLs.")
        if not self.urls:
            raise RuntimeError(
                "No approved HTML list URLs configured. Set APPROVED_HTML_LIST_URLS only for pages where "
                "automated collection and data reuse are explicitly permitted."
            )

        products: list[Product] = []
        seen_urls: set[str] = set()
        product_limit = min(limit, MAX_LIST_PRODUCTS)

        for index, url in enumerate(self.urls):
            site_config = self._site_config_for_url(url)
            self._ensure_allowed_by_robots(url)
            parsed = self.list_parser.parse(self._fetch(url), source_url=url, site_config=site_config, limit=product_limit)
            for product in parsed:
                canonical_url = str(product.product_url)
                if canonical_url in seen_urls:
                    continue
                seen_urls.add(canonical_url)
                products.append(product)
                if len(products) >= product_limit:
                    return products
            if index < len(self.urls) - 1:
                time.sleep(self.delay_seconds)

        return products

    def _load_urls(self) -> list[str]:
        raw = os.getenv("APPROVED_HTML_LIST_URLS", "")
        return [url.strip() for url in raw.split(",") if url.strip()]

    def _load_site_configs(self) -> list[HtmlListSiteConfig]:
        if not self.selector_config_path.exists():
            return []
        with self.selector_config_path.open(encoding="utf-8") as config_file:
            raw = yaml.safe_load(config_file) or {}
        return [HtmlListSiteConfig.from_mapping(site) for site in raw.get("sites", [])]

    def _site_config_for_url(self, url: str) -> HtmlListSiteConfig:
        for site_config in self.site_configs:
            if site_config.matches(url):
                return site_config
        raise RuntimeError(
            "No explicitly approved selector config found for this URL. Add selectors and permission notes "
            "to APPROVED_HTML_SELECTOR_CONFIG before collecting."
        )

    def _fetch(self, url: str) -> str:
        response = requests.get(
            url,
            headers={"User-Agent": self.user_agent},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return response.text

    def _ensure_allowed_by_robots(self, url: str) -> None:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        response = requests.get(
            robots_url,
            headers={"User-Agent": self.user_agent},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()

        robot_parser = RobotFileParser()
        robot_parser.set_url(robots_url)
        robot_parser.parse(response.text.splitlines())
        if not robot_parser.can_fetch(self.user_agent, url):
            raise RuntimeError(f"robots.txt does not allow fetching this URL: {url}")
