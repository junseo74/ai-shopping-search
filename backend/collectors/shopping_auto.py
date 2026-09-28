import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import quote_plus

import yaml

from .approved_html import HtmlListSiteConfig, HtmlProductListParser
from .base import BaseCollector, CollectorMetadata

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

try:
    from ..models import PlatformType, Product
except ImportError:
    from models import PlatformType, Product


DEFAULT_SOURCES_CONFIG_PATH = Path(__file__).with_name("shopping_sources.yml")
MAX_AUTO_PRODUCTS = 20


@dataclass(frozen=True)
class ShoppingSourcePermission:
    approved: bool = False
    note: Optional[str] = None
    reference: Optional[str] = None


@dataclass(frozen=True)
class ShoppingSourceConfig:
    name: str
    collection_method: str
    seller: Optional[str]
    list_urls: tuple[str, ...] = ()
    selectors: dict[str, str] = field(default_factory=dict)
    attributes: dict[str, str] = field(default_factory=dict)
    permission: ShoppingSourcePermission = field(default_factory=ShoppingSourcePermission)
    api_collector: Optional[str] = None

    @classmethod
    def from_mapping(cls, raw: dict) -> "ShoppingSourceConfig":
        permission_raw = raw.get("permission") or {}
        permission = ShoppingSourcePermission(
            approved=permission_raw.get("approved") is True,
            note=permission_raw.get("note"),
            reference=permission_raw.get("reference"),
        )
        source = cls(
            name=str(raw.get("name") or "").strip(),
            collection_method=str(raw.get("collection_method") or "").strip(),
            seller=raw.get("seller"),
            list_urls=tuple(str(url).strip() for url in raw.get("list_urls", []) if str(url).strip()),
            selectors={str(key): str(value) for key, value in (raw.get("selectors") or {}).items() if value},
            attributes={str(key): str(value) for key, value in (raw.get("attributes") or {}).items() if value},
            permission=permission,
            api_collector=raw.get("api_collector"),
        )
        source.validate()
        return source

    def validate(self) -> None:
        if not self.name:
            raise ValueError("Shopping source config must include a name.")
        if self.collection_method not in {"api", "approved_html"}:
            raise ValueError(f"Unsupported collection method for {self.name}: {self.collection_method}")
        if not self.permission.approved:
            return
        if not (self.permission.note or self.permission.reference):
            raise ValueError(f"Approved source {self.name} must include a permission note or reference.")
        if self.collection_method == "api" and not self.api_collector:
            raise ValueError(f"Approved API source {self.name} must include api_collector.")
        if self.collection_method == "approved_html":
            required = ["product_card", "product_name", "price", "product_url"]
            missing = [field for field in required if not self.selectors.get(field)]
            if missing:
                raise ValueError(f"Approved HTML source {self.name} is missing selectors: {', '.join(missing)}")
            if not self.list_urls:
                raise ValueError(f"Approved HTML source {self.name} must include list_urls.")

    def as_html_site_config(self, url: str) -> HtmlListSiteConfig:
        return HtmlListSiteConfig(
            name=self.name,
            domains=(self._hostname_from_url(url),),
            selectors=self.selectors,
            attributes=self.attributes,
            default_seller=self.seller,
            permission_note=self.permission.note,
            permission_reference=self.permission.reference,
        )

    def urls_for_query(self, query: str) -> list[str]:
        encoded = quote_plus(query)
        return [url.replace("{query}", encoded) for url in self.list_urls]

    def _hostname_from_url(self, url: str) -> str:
        from urllib.parse import urlparse

        return (urlparse(url).hostname or "").lower()


@dataclass(frozen=True)
class ShoppingSourceFailure:
    source_name: str
    error_message: str
    response_time_ms: float


class ShoppingAutoCollector(BaseCollector):
    metadata = CollectorMetadata(
        source_name="shopping_auto",
        platform=PlatformType.SHOPPING_MALL,
        requires_api_key=False,
    )

    def __init__(
        self,
        config_path: Optional[str | Path] = None,
        api_collectors: Optional[dict[str, BaseCollector]] = None,
        html_parser: Optional[HtmlProductListParser] = None,
        html_fetcher: Optional[Callable[[str], str]] = None,
        robots_checker: Optional[Callable[[str], None]] = None,
    ) -> None:
        if load_dotenv:
            load_dotenv()
        self.config_path = Path(config_path or os.getenv("SHOPPING_SOURCES_CONFIG", str(DEFAULT_SOURCES_CONFIG_PATH)))
        self.api_collectors = api_collectors or {}
        self.html_parser = html_parser or HtmlProductListParser()
        self.html_fetcher = html_fetcher
        self.robots_checker = robots_checker
        self.delay_seconds = float(os.getenv("SHOPPING_AUTO_DELAY_SECONDS", "1.0"))
        self.sources = self._load_sources()
        self.last_failures: list[ShoppingSourceFailure] = []

    def collect(self, query: str | None = None, limit: int = 20) -> list[Product]:
        if not query:
            raise ValueError("Automatic shopping collection requires a search query.")

        self.last_failures = []
        products: list[Product] = []
        seen_urls: set[str] = set()
        product_limit = min(limit, MAX_AUTO_PRODUCTS)
        approved_sources = [source for source in self.sources if source.permission.approved]

        for index, source in enumerate(approved_sources):
            started = time.perf_counter()
            try:
                source_products = self._collect_source(source, query=query, limit=product_limit)
                self._merge_products(products, seen_urls, source_products, product_limit)
            except Exception as exc:
                elapsed_ms = (time.perf_counter() - started) * 1000
                self.last_failures.append(
                    ShoppingSourceFailure(
                        source_name=source.name,
                        error_message=str(exc),
                        response_time_ms=round(elapsed_ms, 2),
                    )
                )
            if len(products) >= product_limit:
                break
            if index < len(approved_sources) - 1:
                time.sleep(self.delay_seconds)

        return products

    def configured_source_count(self) -> int:
        return len(self.sources)

    def approved_source_count(self) -> int:
        return sum(source.permission.approved for source in self.sources)

    def _load_sources(self) -> list[ShoppingSourceConfig]:
        if not self.config_path.exists():
            return []
        with self.config_path.open(encoding="utf-8") as config_file:
            raw = yaml.safe_load(config_file) or {}
        return [ShoppingSourceConfig.from_mapping(source) for source in raw.get("sources", [])]

    def _collect_source(self, source: ShoppingSourceConfig, query: str, limit: int) -> list[Product]:
        if source.collection_method == "api":
            collector = self.api_collectors.get(source.api_collector or "")
            if not collector:
                raise RuntimeError(f"API collector is not registered: {source.api_collector}")
            return [
                self._normalize_product(product, source)
                for product in collector.collect(query=query, limit=limit)
                if product.product_url
            ]

        products: list[Product] = []
        for url in source.urls_for_query(query):
            self._ensure_allowed_by_robots(url)
            html = self._fetch_html(url)
            site_config = source.as_html_site_config(url)
            products.extend(self.html_parser.parse(html, source_url=url, site_config=site_config, limit=limit))
            if len(products) >= limit:
                break
        return [self._normalize_product(product, source) for product in products if product.product_url]

    def _merge_products(
        self,
        products: list[Product],
        seen_urls: set[str],
        source_products: list[Product],
        limit: int,
    ) -> None:
        for product in source_products:
            product_url = str(product.product_url)
            if product_url in seen_urls:
                continue
            seen_urls.add(product_url)
            products.append(product)
            if len(products) >= limit:
                return

    def _normalize_product(self, product: Product, source: ShoppingSourceConfig) -> Product:
        return product.model_copy(
            update={
                "seller": product.seller or source.seller,
                "data_source": source.name,
            }
        )

    def _fetch_html(self, url: str) -> str:
        if self.html_fetcher:
            return self.html_fetcher(url)

        from .approved_html import ApprovedHtmlProductCollector

        return ApprovedHtmlProductCollector()._fetch(url)

    def _ensure_allowed_by_robots(self, url: str) -> None:
        if self.robots_checker:
            self.robots_checker(url)
            return

        from .approved_html import ApprovedHtmlProductCollector

        ApprovedHtmlProductCollector()._ensure_allowed_by_robots(url)
