import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, unquote, urlencode, urlparse, urlunparse

try:
    from backend.tools.naver_shopping_html_analyzer import (
        DEFAULT_SOURCE_URL,
        ExtractedNaverAdProduct,
        NaverShoppingHtmlAnalyzer,
    )
except ImportError:  # pragma: no cover - supports running from backend dir.
    from naver_shopping_html_analyzer import DEFAULT_SOURCE_URL, ExtractedNaverAdProduct, NaverShoppingHtmlAnalyzer


HTML_SUFFIXES = {".html", ".htm"}
MISSING_FIELDS = ["product_name", "price", "shipping_fee", "seller", "product_url", "image_url"]
TRACKING_QUERY_PREFIXES = ("utm_",)
TRACKING_QUERY_KEYS = {
    "adId",
    "channel",
    "clid",
    "entryPoint",
    "n_ad",
    "NaPm",
    "query",
    "timestamp",
    "tracking",
}


@dataclass(frozen=True)
class FileExtractionSummary:
    file_path: str
    source_url: str
    source_query: Optional[str]
    extracted_count: int
    ad_count: int
    organic_count: int
    missing_fields: dict[str, int]


@dataclass(frozen=True)
class MergeExtractionSummary:
    file_count: int
    total_extracted_count: int
    duplicate_count: int
    final_product_count: int
    ad_count: int
    organic_count: int
    missing_fields: dict[str, int]
    files: list[FileExtractionSummary]


class ShoppingHtmlMerger:
    """Merge products from local saved shopping HTML files.

    The merger performs no network requests. Naver extraction is delegated to
    NaverShoppingHtmlAnalyzer so selector and __NEXT_DATA__ parsing behavior
    stays in one place.
    """

    def __init__(self, analyzer: Optional[NaverShoppingHtmlAnalyzer] = None):
        self.analyzer = analyzer or NaverShoppingHtmlAnalyzer()

    def merge_paths(
        self,
        inputs: list[str | Path],
        source_url: str = DEFAULT_SOURCE_URL,
    ) -> tuple[list[dict[str, object]], MergeExtractionSummary]:
        html_paths = discover_html_paths(inputs)
        products: list[dict[str, object]] = []
        files: list[FileExtractionSummary] = []
        seen_keys: set[tuple[str, str]] = set()
        duplicate_count = 0
        total_extracted_count = 0

        for html_path in html_paths:
            extracted, file_summary = self.analyzer.extract_all_products_file(
                html_path=html_path,
                source_url=source_url,
            )
            rows = [self._product_row(product, html_path) for product in extracted]
            total_extracted_count += len(rows)
            files.append(
                FileExtractionSummary(
                    file_path=str(html_path),
                    source_url=rows[0]["source_url"] if rows else source_url,
                    source_query=rows[0]["source_query"] if rows else _query_from_source_url(source_url),
                    extracted_count=len(rows),
                    ad_count=file_summary.ad_count,
                    organic_count=file_summary.organic_count,
                    missing_fields=_missing_fields(rows),
                )
            )

            for row in rows:
                key = product_identity_key(row)
                if key in seen_keys:
                    duplicate_count += 1
                    continue
                seen_keys.add(key)
                products.append(row)

        summary = MergeExtractionSummary(
            file_count=len(html_paths),
            total_extracted_count=total_extracted_count,
            duplicate_count=duplicate_count,
            final_product_count=len(products),
            ad_count=sum(1 for product in products if product.get("product_type") == "ad"),
            organic_count=sum(1 for product in products if product.get("product_type") == "organic"),
            missing_fields=_missing_fields(products),
            files=files,
        )
        return products, summary

    def write_json(
        self,
        products: list[dict[str, object]],
        summary: MergeExtractionSummary,
        output_path: str | Path,
    ) -> None:
        payload = {"summary": asdict(summary), "products": products}
        Path(output_path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def format_result(self, products: list[dict[str, object]], summary: MergeExtractionSummary) -> str:
        return json.dumps({"summary": asdict(summary), "products": products}, ensure_ascii=False, indent=2)

    def _product_row(self, product: ExtractedNaverAdProduct, html_path: Path) -> dict[str, object]:
        row = asdict(product)
        row["source_query"] = _query_from_source_url(product.source_url)
        row["source_file"] = str(html_path)
        row["dedupe_key"] = product_identity_key(row)
        return row


def discover_html_paths(inputs: list[str | Path]) -> list[Path]:
    paths: list[Path] = []
    for value in inputs:
        path = Path(value)
        if path.is_dir():
            paths.extend(sorted(child for child in path.rglob("*") if child.suffix.lower() in HTML_SUFFIXES))
        elif path.is_file() and path.suffix.lower() in HTML_SUFFIXES:
            paths.append(path)
        elif path.is_file():
            continue
        else:
            raise FileNotFoundError(f"HTML input path does not exist: {path}")
    return _unique_paths(paths)


def product_identity_key(product: dict[str, object]) -> tuple[str, str]:
    product_url = product.get("product_url")
    if isinstance(product_url, str) and product_url.strip():
        product_id = _product_id_from_url(product_url)
        if product_id:
            return ("product_id", product_id)
        return ("product_url", normalize_product_url(product_url))

    seller = product.get("seller")
    product_name = product.get("product_name")
    if isinstance(seller, str) and seller.strip() and isinstance(product_name, str) and product_name.strip():
        return ("seller_name", f"{_normalize_text(seller)}::{_normalize_text(product_name)}")

    source_file = product.get("source_file")
    if isinstance(product_name, str) and product_name.strip() and isinstance(source_file, str) and source_file.strip():
        return ("source_file_name", f"{source_file}::{_normalize_text(product_name)}")
    return ("unknown", json.dumps(product, ensure_ascii=False, sort_keys=True))


def normalize_product_url(product_url: str) -> str:
    parsed = urlparse(product_url.strip())
    query_items = []
    for key, values in parse_qs(parsed.query, keep_blank_values=True).items():
        if key in TRACKING_QUERY_KEYS or any(key.startswith(prefix) for prefix in TRACKING_QUERY_PREFIXES):
            continue
        for value in values:
            query_items.append((key, value))
    query_items.sort()
    normalized = parsed._replace(
        scheme=parsed.scheme.lower(),
        netloc=parsed.netloc.lower(),
        path=_normalize_path(parsed.path),
        params="",
        query=urlencode(query_items, doseq=True),
        fragment="",
    )
    return urlunparse(normalized)


def _product_id_from_url(product_url: str) -> Optional[str]:
    parsed = urlparse(product_url.strip())
    host = parsed.netloc.lower()
    path = parsed.path
    smartstore = re.search(r"/products/(\d+)", path)
    if smartstore and ("smartstore.naver.com" in host or "brand.naver.com" in host):
        return f"{host}:products:{smartstore.group(1)}"

    query = parse_qs(parsed.query)
    for key in ("nvMid", "cat_id", "catalogId", "productId", "itemId", "goodsNo"):
        value = query.get(key)
        if value and value[0]:
            return f"{host}:{key}:{value[0]}"
    return None


def _missing_fields(products: list[dict[str, object]]) -> dict[str, int]:
    return {
        field: sum(product.get(field) in (None, "") for product in products)
        for field in MISSING_FIELDS
    }


def _query_from_source_url(source_url: Optional[str]) -> Optional[str]:
    if not source_url:
        return None
    parsed = urlparse(source_url)
    query = parse_qs(parsed.query).get("query")
    if not query or not query[0]:
        return None
    return unquote(query[0])


def _normalize_path(path: str) -> str:
    if not path:
        return ""
    return re.sub(r"/+", "/", path).rstrip("/") or "/"


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def _unique_paths(paths: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    result: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        result.append(path)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge products from local saved shopping HTML files.")
    parser.add_argument("inputs", nargs="+", help="Saved HTML files or folders containing .html/.htm files.")
    parser.add_argument("--source-url", default=DEFAULT_SOURCE_URL)
    parser.add_argument("--output-json", default="merged_products.json")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    merger = ShoppingHtmlMerger()
    products, summary = merger.merge_paths(args.inputs, source_url=args.source_url)
    merger.write_json(products, summary, args.output_json)

    if args.format == "json":
        print(merger.format_result(products, summary))
        return

    print(f"files: {summary.file_count}")
    for file_summary in summary.files:
        print(
            "file: {file_path} | extracted: {extracted_count} | ads: {ad_count} | organic: {organic_count} | query: {source_query} | missing: {missing_fields}".format(
                file_path=file_summary.file_path,
                extracted_count=file_summary.extracted_count,
                ad_count=file_summary.ad_count,
                organic_count=file_summary.organic_count,
                source_query=file_summary.source_query or "",
                missing_fields=json.dumps(file_summary.missing_fields, ensure_ascii=False, sort_keys=True),
            )
        )
    print(f"total_extracted_count: {summary.total_extracted_count}")
    print(f"duplicate_count: {summary.duplicate_count}")
    print(f"final_product_count: {summary.final_product_count}")
    print(f"ad_count: {summary.ad_count}")
    print(f"organic_count: {summary.organic_count}")
    print(f"missing_fields: {json.dumps(summary.missing_fields, ensure_ascii=False, sort_keys=True)}")
    print(f"output_json: {args.output_json}")


if __name__ == "__main__":
    main()
