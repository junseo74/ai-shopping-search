import argparse
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional
from urllib.parse import quote_plus, urlparse
from urllib.robotparser import RobotFileParser

import requests
import yaml

try:
    from backend.collectors.approved_html import HtmlListSiteConfig, HtmlProductListParser
    from backend.tools.merge_shopping_html import MISSING_FIELDS, normalize_product_url, product_identity_key
except ImportError:  # pragma: no cover - supports running from backend dir.
    from collectors.approved_html import HtmlListSiteConfig, HtmlProductListParser
    from merge_shopping_html import MISSING_FIELDS, normalize_product_url, product_identity_key


DEFAULT_USER_AGENT = "ai-shopping-search/0.1 (+approved-local-html-collection)"


@dataclass(frozen=True)
class AutoHtmlSourceConfig:
    name: str
    search_url_template: str
    selectors: dict[str, str]
    attributes: dict[str, str]
    permission_note: str
    permission_reference: Optional[str] = None
    default_seller: Optional[str] = None
    page_start: int = 1
    page_param_step: int = 1

    @classmethod
    def from_mapping(cls, raw: dict[str, Any]) -> "AutoHtmlSourceConfig":
        permission = raw.get("permission") or {}
        if permission.get("approved") is not True:
            raise ValueError(f"Source {raw.get('name', '<unnamed>')} is not explicitly approved.")
        if not (permission.get("note") or permission.get("reference")):
            raise ValueError(f"Source {raw.get('name', '<unnamed>')} must include permission note or reference.")

        selectors = {str(key): str(value) for key, value in (raw.get("selectors") or {}).items() if value}
        missing = [field for field in ("product_card", "product_name", "price", "product_url") if not selectors.get(field)]
        if missing:
            raise ValueError(f"Source {raw.get('name', '<unnamed>')} is missing selectors: {', '.join(missing)}")

        search_url_template = str(raw.get("search_url_template") or "").strip()
        if "{query}" not in search_url_template:
            raise ValueError(f"Source {raw.get('name', '<unnamed>')} search_url_template must include {{query}}.")

        name = str(raw.get("name") or "").strip()
        if not name:
            raise ValueError("Auto HTML source config must include a name.")

        return cls(
            name=name,
            search_url_template=search_url_template,
            selectors=selectors,
            attributes={str(key): str(value) for key, value in (raw.get("attributes") or {}).items() if value},
            default_seller=raw.get("default_seller"),
            permission_note=str(permission.get("note") or ""),
            permission_reference=permission.get("reference"),
            page_start=int(raw.get("page_start", 1)),
            page_param_step=int(raw.get("page_param_step", 1)),
        )

    def url_for_page(self, query: str, page_index: int) -> str:
        page_value = self.page_start + (page_index * self.page_param_step)
        return self.search_url_template.format(query=quote_plus(query), page=page_value)

    def as_site_config(self, url: str) -> HtmlListSiteConfig:
        hostname = urlparse(url).hostname or ""
        return HtmlListSiteConfig(
            name=self.name,
            domains=(hostname.lower(),),
            selectors=self.selectors,
            attributes=self.attributes,
            default_seller=self.default_seller,
            permission_note=self.permission_note,
            permission_reference=self.permission_reference,
        )


@dataclass(frozen=True)
class AutoHtmlPageSummary:
    page: int
    url: str
    status: str
    extracted_count: int = 0
    unique_added_count: int = 0
    duplicate_count: int = 0
    response_time_ms: float = 0
    error_message: Optional[str] = None


@dataclass(frozen=True)
class AutoHtmlSummary:
    source_name: str
    query: str
    requested_pages: int
    successful_pages: int
    total_extracted_count: int
    duplicate_count: int
    final_product_count: int
    missing_fields: dict[str, int]
    pages: list[AutoHtmlPageSummary]


class AutoShoppingHtmlCollector:
    def __init__(
        self,
        source: AutoHtmlSourceConfig,
        parser: Optional[HtmlProductListParser] = None,
        session: Optional[requests.Session] = None,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout_seconds: float = 10.0,
        delay_seconds: float = 1.0,
    ) -> None:
        self.source = source
        self.parser = parser or HtmlProductListParser()
        self.session = session or requests.Session()
        self.user_agent = user_agent
        self.timeout_seconds = timeout_seconds
        self.delay_seconds = delay_seconds

    def collect(self, query: str, max_pages: int = 1, per_page_limit: int = 50) -> tuple[list[dict[str, object]], AutoHtmlSummary]:
        if not query:
            raise ValueError("Search query is required.")
        if max_pages < 1:
            raise ValueError("max_pages must be at least 1.")

        products: list[dict[str, object]] = []
        seen_keys: set[tuple[str, str]] = set()
        page_summaries: list[AutoHtmlPageSummary] = []
        total_extracted = 0
        duplicate_count = 0

        for page_index in range(max_pages):
            page_number = page_index + 1
            url = self.source.url_for_page(query, page_index)
            started = time.perf_counter()
            try:
                self._ensure_allowed_by_robots(url)
                html = self._fetch(url)
                parsed = self.parser.parse(
                    html,
                    source_url=url,
                    site_config=self.source.as_site_config(url),
                    limit=per_page_limit,
                )
                rows = [self._product_to_row(product, query, page_number, self.source.name) for product in parsed]
                total_extracted += len(rows)
                page_duplicates = 0
                page_added = 0
                for row in rows:
                    key = product_identity_key(row)
                    if key in seen_keys:
                        duplicate_count += 1
                        page_duplicates += 1
                        continue
                    seen_keys.add(key)
                    row["dedupe_key"] = key
                    products.append(row)
                    page_added += 1
                page_summaries.append(
                    AutoHtmlPageSummary(
                        page=page_number,
                        url=url,
                        status="success",
                        extracted_count=len(rows),
                        unique_added_count=page_added,
                        duplicate_count=page_duplicates,
                        response_time_ms=round((time.perf_counter() - started) * 1000, 2),
                    )
                )
            except Exception as exc:
                page_summaries.append(
                    AutoHtmlPageSummary(
                        page=page_number,
                        url=url,
                        status="failed",
                        response_time_ms=round((time.perf_counter() - started) * 1000, 2),
                        error_message=str(exc),
                    )
                )

            if page_index < max_pages - 1:
                time.sleep(self.delay_seconds)

        summary = AutoHtmlSummary(
            source_name=self.source.name,
            query=query,
            requested_pages=max_pages,
            successful_pages=sum(page.status == "success" for page in page_summaries),
            total_extracted_count=total_extracted,
            duplicate_count=duplicate_count,
            final_product_count=len(products),
            missing_fields=_missing_fields(products),
            pages=page_summaries,
        )
        return products, summary

    def _fetch(self, url: str) -> str:
        response = self.session.get(url, headers={"User-Agent": self.user_agent}, timeout=self.timeout_seconds)
        response.raise_for_status()
        return response.text

    def _ensure_allowed_by_robots(self, url: str) -> None:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        response = self.session.get(robots_url, headers={"User-Agent": self.user_agent}, timeout=self.timeout_seconds)
        response.raise_for_status()
        robot_parser = RobotFileParser()
        robot_parser.set_url(robots_url)
        robot_parser.parse(response.text.splitlines())
        if not robot_parser.can_fetch(self.user_agent, url):
            raise RuntimeError(f"robots.txt does not allow fetching this URL: {url}")

    def _product_to_row(self, product, query: str, page: int, source_name: str) -> dict[str, object]:
        product_url = str(product.product_url) if product.product_url else None
        image_url = str(product.image_url) if product.image_url else None
        row = {
            "product_name": product.product_name,
            "price": product.price,
            "original_price": product.original_price,
            "shipping_fee": product.shipping_fee,
            "seller": product.seller,
            "product_url": product_url,
            "image_url": image_url,
            "platform": product.platform,
            "source_url": str(product.source_url) if product.source_url else None,
            "source_query": query,
            "source_page": page,
            "source_name": source_name,
            "data_source": f"auto_html:{source_name}",
        }
        row["normalized_product_url"] = normalize_product_url(product_url) if product_url else None
        return row


def load_source_config(config_path: str | Path, source_name: Optional[str] = None) -> AutoHtmlSourceConfig:
    with Path(config_path).open(encoding="utf-8") as config_file:
        raw = yaml.safe_load(config_file) or {}
    sources = [AutoHtmlSourceConfig.from_mapping(source) for source in raw.get("sources", [])]
    if not sources:
        raise ValueError("No approved auto HTML sources configured.")
    if source_name:
        for source in sources:
            if source.name == source_name:
                return source
        raise ValueError(f"Source not found in config: {source_name}")
    if len(sources) > 1:
        raise ValueError("Multiple sources configured. Pass --source-name.")
    return sources[0]


def write_result_json(products: list[dict[str, object]], summary: AutoHtmlSummary, output_path: str | Path) -> None:
    payload = {"summary": asdict(summary), "products": products}
    Path(output_path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def format_result(products: list[dict[str, object]], summary: AutoHtmlSummary) -> str:
    return json.dumps({"summary": asdict(summary), "products": products}, ensure_ascii=False, indent=2)


def _missing_fields(products: list[dict[str, object]]) -> dict[str, int]:
    return {
        field: sum(product.get(field) in (None, "") for product in products)
        for field in MISSING_FIELDS
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect approved shopping search HTML pages automatically.")
    parser.add_argument("--config", required=True, help="YAML config with explicitly approved source settings.")
    parser.add_argument("--source-name", help="Source name when the config contains multiple sources.")
    parser.add_argument("--query", required=True, help="Search query.")
    parser.add_argument("--max-pages", type=int, default=1)
    parser.add_argument("--per-page-limit", type=int, default=50)
    parser.add_argument("--delay-seconds", type=float, default=1.0)
    parser.add_argument("--timeout-seconds", type=float, default=10.0)
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    parser.add_argument("--output-json", default="auto_collected_products.json")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    source = load_source_config(args.config, args.source_name)
    collector = AutoShoppingHtmlCollector(
        source=source,
        user_agent=args.user_agent,
        timeout_seconds=args.timeout_seconds,
        delay_seconds=args.delay_seconds,
    )
    products, summary = collector.collect(
        query=args.query,
        max_pages=args.max_pages,
        per_page_limit=args.per_page_limit,
    )
    write_result_json(products, summary, args.output_json)

    if args.format == "json":
        print(format_result(products, summary))
        return

    print(f"source_name: {summary.source_name}")
    print(f"query: {summary.query}")
    for page in summary.pages:
        print(
            "page: {page} | status: {status} | extracted: {extracted_count} | unique_added: {unique_added_count} | duplicates: {duplicate_count} | ms: {response_time_ms} | url: {url}{error}".format(
                page=page.page,
                status=page.status,
                extracted_count=page.extracted_count,
                unique_added_count=page.unique_added_count,
                duplicate_count=page.duplicate_count,
                response_time_ms=page.response_time_ms,
                url=page.url,
                error=f" | error: {page.error_message}" if page.error_message else "",
            )
        )
    print(f"successful_pages: {summary.successful_pages}/{summary.requested_pages}")
    print(f"total_extracted_count: {summary.total_extracted_count}")
    print(f"duplicate_count: {summary.duplicate_count}")
    print(f"final_product_count: {summary.final_product_count}")
    print(f"missing_fields: {json.dumps(summary.missing_fields, ensure_ascii=False, sort_keys=True)}")
    print(f"output_json: {args.output_json}")


if __name__ == "__main__":
    main()
