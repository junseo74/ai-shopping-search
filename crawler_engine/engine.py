from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

from .aggregation import aggregate_candidates, product_identity
from .eligibility import is_eligible_product_candidate
from .extractors._html import extract_scripts
from .extractors import (
    extract_dom_candidates,
    extract_embedded_data_candidates,
    extract_json_ld_candidates,
    extract_site_specific_candidates,
)
from .extractors.dom_candidates import count_links, count_product_like_links
from .models import CrawlRequest, CrawlResult, CrawledProduct, ProductCandidate, SourceMetadata
from .normalize import normalize_candidate
from .outputs import save_result
from .sources import select_sources
from .validators import dedupe_products, is_valid_product


SUCCESS = "success"
NO_RESULTS = "no_results"
ACCESS_ERROR = "access_error"
RENDER_ERROR = "render_error"


class CrawlerEngine:
    def __init__(
        self,
        timeout_ms: int = 30000,
        headless: bool = True,
        debug: bool = False,
        save_debug_html: bool = False,
        output_dir: Path | str = "crawler_output",
    ) -> None:
        self.timeout_ms = timeout_ms
        self.headless = headless
        self.debug = debug
        self.save_debug_html = save_debug_html
        self.output_dir = Path(output_dir)
        self._last_render_debug: dict[str, object] = {}

    def crawl(self, request: CrawlRequest, source_name: Optional[str] = None) -> CrawlResult:
        products: list[CrawledProduct] = []
        errors: list[str] = []
        debug_payload: dict[str, object] = {}
        sources = select_sources(request, source_name)
        if source_name and not sources:
            return CrawlResult(
                query=request.query,
                source=source_name,
                products=[],
                status=NO_RESULTS,
                errors=[f"Source '{source_name}' was skipped because include_used is false."],
                debug={"requested_source": source_name, "include_used": request.include_used},
            )

        for source in sources:
            url = source.build_search_url(request)
            try:
                html = self.render_page(url)
                debug_payload[source.metadata.source] = self.inspect_page(html, source.metadata)
                access_error = self.detect_access_error(debug_payload[source.metadata.source])
                if access_error:
                    errors.append(f"{source.metadata.source}: {access_error}")
                    continue
                candidates = self.extract_candidates(html, source.metadata, limit=request.limit * 8, query=request.query)
                raw_image_candidate_count = sum(1 for candidate in candidates if candidate.image_url)
                candidates = aggregate_candidates(
                    candidates,
                    source.metadata,
                    url,
                    query=request.query,
                    include_used=request.include_used,
                )
                aggregated_candidate_count = len(candidates)
                aggregated_candidates = candidates
                candidates = [
                    candidate
                    for candidate in candidates
                    if is_eligible_product_candidate(candidate, source.metadata, url)
                ]
                if isinstance(debug_payload[source.metadata.source], dict):
                    debug_payload[source.metadata.source]["raw_image_candidate_count"] = raw_image_candidate_count
                    debug_payload[source.metadata.source]["image_candidates_with_identity_count"] = sum(
                        1 for candidate in aggregated_candidates if candidate.image_url and product_identity(candidate, source.metadata, url)
                    )
                    if self.debug:
                        debug_payload[source.metadata.source]["image_candidate_identity_examples"] = [
                            {
                                "identity": product_identity(candidate, source.metadata, url),
                                "image_url": candidate.image_url,
                                "product_url": candidate.product_url,
                            }
                            for candidate in aggregated_candidates
                            if candidate.image_url and product_identity(candidate, source.metadata, url)
                        ][:5]
                    debug_payload[source.metadata.source]["aggregated_candidate_count"] = aggregated_candidate_count
                    debug_payload[source.metadata.source]["aggregated_image_candidate_count"] = sum(
                        1 for candidate in candidates if candidate.image_url
                    )
                    debug_payload[source.metadata.source]["normalized_candidate_count"] = len(candidates)
                if self.debug and self.save_debug_html:
                    debug_path = self.output_dir / f"debug_{source.metadata.source}.html"
                    debug_path.parent.mkdir(parents=True, exist_ok=True)
                    debug_path.write_text(html, encoding="utf-8")
                    if isinstance(debug_payload[source.metadata.source], dict):
                        debug_payload[source.metadata.source]["debug_html_path"] = str(debug_path)
                for candidate in candidates:
                    product = normalize_candidate(candidate, source.metadata, url)
                    if product and is_valid_product(product, request.max_price):
                        products.append(product)
                    if len(products) >= request.limit:
                        break
            except Exception as exc:
                errors.append(f"{source.metadata.source}: {exc}")
                debug_payload[source.metadata.source] = {
                    **self._last_render_debug,
                    "render_error": str(exc),
                }

        products = dedupe_products(products)[: request.limit]
        status, error = self._result_status(products, errors, debug_payload)
        return CrawlResult(
            query=request.query,
            source=source_name,
            products=products,
            status=status,
            error=error,
            errors=errors,
            debug=debug_payload if self.debug else {},
        )

    def inspect_page(self, html: str, metadata: SourceMetadata | None = None) -> dict[str, object]:
        scripts = extract_scripts(html)
        json_ld_count = sum(1 for script in scripts if "ld+json" in ((script.get("type") or "").lower()))
        embedded_candidates = extract_embedded_data_candidates(html)
        url_hints = metadata.product_url_hints if metadata else ()
        dom_candidates = extract_dom_candidates(html, product_url_hints=url_hints)
        return {
            **self._last_render_debug,
            "html_length": len(html),
            "json_ld_script_count": json_ld_count,
            "embedded_json_candidate_count": len(embedded_candidates),
            "total_link_count": count_links(html),
            "product_like_link_count": count_product_like_links(html, product_url_hints=url_hints),
            "dom_candidate_count": len(dom_candidates),
        }

    def detect_access_error(self, debug: object) -> str | None:
        if not isinstance(debug, dict):
            return None
        title = str(debug.get("title") or "").lower()
        html_length = int(debug.get("html_length") or 0)
        link_count = int(debug.get("total_link_count") or 0)
        http_status = debug.get("http_status")
        if isinstance(http_status, int) and http_status >= 400:
            return f"Source returned HTTP status {http_status}"
        error_titles = (
            "the request could not be satisfied",
            "access denied",
            "forbidden",
            "error",
        )
        if any(marker in title for marker in error_titles) and html_length < 5000 and link_count == 0:
            return "Source returned an error page"
        return None

    def _result_status(
        self,
        products: list[CrawledProduct],
        errors: list[str],
        debug_payload: dict[str, object],
    ) -> tuple[str, str | None]:
        if products:
            return SUCCESS, None
        if any(
            isinstance(debug, dict) and "render_error" in debug
            for debug in debug_payload.values()
        ):
            return RENDER_ERROR, errors[0] if errors else "Render failed"
        if errors:
            return ACCESS_ERROR, errors[0]
        return NO_RESULTS, None

    def extract_candidates(
        self,
        html: str,
        metadata: SourceMetadata | None = None,
        limit: int = 100,
        query: str | None = None,
    ) -> list[ProductCandidate]:
        candidates: list[ProductCandidate] = []
        candidates.extend(extract_site_specific_candidates(html, metadata, limit=limit, query=query))
        if candidates:
            return candidates[:limit]
        candidates.extend(extract_json_ld_candidates(html))
        if len(candidates) < limit:
            candidates.extend(extract_embedded_data_candidates(html, limit=limit))
        if len(candidates) < limit:
            url_hints = metadata.product_url_hints if metadata else ()
            candidates.extend(extract_dom_candidates(html, limit=limit, product_url_hints=url_hints, query=query))
        return candidates[:limit]

    def render_page(self, url: str) -> str:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError(
                "Playwright is required for live rendering. Install crawler_engine/requirements.txt "
                "and run `playwright install chromium`."
            ) from exc

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                channel="chrome",
                headless=self.headless,
            )
            page = browser.new_page()
            response = None
            try:
                response = page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_ms)
                page.wait_for_load_state("networkidle", timeout=self.timeout_ms)
                page.wait_for_function(
                    "() => /[0-9][0-9,\\s]*\\s*\\uC6D0/.test(document.body ? document.body.innerText : '')",
                    timeout=5000,
                )
            except Exception:
                pass
            self._last_render_debug = {
                "requested_url": url,
                "final_url": page.url,
                "title": page.title(),
                "http_status": response.status if response else None,
            }
            html = page.content()
            browser.close()
        return html


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the standalone shopping crawler engine.")
    parser.add_argument("query")
    parser.add_argument("--source", default=None)
    parser.add_argument("--max-price", type=int, default=None)
    parser.add_argument("--include-used", action="store_true")
    parser.add_argument("--country", default="KR")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--output-dir", default="crawler_output")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--save-debug-html", action="store_true")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    request = CrawlRequest(
        query=args.query,
        max_price=args.max_price,
        include_used=args.include_used,
        country=args.country,
        limit=args.limit,
    )
    engine = CrawlerEngine(
        headless=not args.headed,
        debug=args.debug,
        save_debug_html=args.save_debug_html,
        output_dir=args.output_dir,
    )
    result = engine.crawl(request, source_name=args.source)
    source_part = args.source or "all"
    safe_query = "".join(ch if ch.isalnum() else "_" for ch in args.query).strip("_") or "query"
    output_path = Path(args.output_dir) / f"{source_part}_{safe_query}.json"
    save_result(result, output_path)
    print(f"Saved {len(result.products)} products to {output_path}")
    if result.errors:
        print("Errors:")
        for error in result.errors:
            print(f"- {error}")
    if args.debug:
        print("Debug:")
        for source, debug in result.debug.items():
            print(f"- {source}: {debug}")
    return 0 if result.products or not result.errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
