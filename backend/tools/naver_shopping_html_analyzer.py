import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional
from urllib.parse import quote, urljoin

import yaml
from bs4 import BeautifulSoup


PRICE_RE = re.compile(r"\d[\d,.\s]*")
DEFAULT_SOURCE_URL = "https://search.shopping.naver.com/search/all?query={query}"
NAVER_AD_SELECTORS = {
    "product_card": ".adProduct_item__T7utB",
    "product_name": ".adProduct_link__hNwpz",
    "price": ".price_num__Y66T7",
    "shipping_fee": ".price_delivery_fee__8n1e5",
    "seller": ".adProduct_mall__grJaU",
    "product_url": ".adProduct_link__hNwpz",
}
NAVER_AD_ATTRIBUTES = {"product_url": "href"}


@dataclass(frozen=True)
class SelectorCandidate:
    selector: str
    match_count: int
    matching_cards: int
    sample_values: list[str]


@dataclass(frozen=True)
class HtmlAnalysisResult:
    source_name: str
    source_url: str
    card_candidates: list[SelectorCandidate]
    field_candidates: dict[str, list[SelectorCandidate]]


@dataclass(frozen=True)
class ExtractedNaverAdProduct:
    product_name: str
    product_type: str
    price: Optional[float]
    original_price: Optional[float]
    shipping_fee: Optional[float]
    seller: Optional[str]
    product_url: Optional[str]
    image_url: Optional[str]
    source_url: str


@dataclass(frozen=True)
class NaverExtractionSummary:
    total_before_dedup: int
    total_after_dedup: int
    ad_count: int
    organic_count: int
    duplicate_count: int
    missing_fields: dict[str, int]


class NaverShoppingHtmlAnalyzer:
    """Find local selector candidates from saved Naver Shopping HTML.

    This analyzer never performs network requests and never marks a source as
    approved. Its output is a review aid, not a finalized parser config.
    """

    def analyze_file(
        self,
        html_path: str | Path,
        source_url: str = DEFAULT_SOURCE_URL,
        source_name: str = "naver_shopping_structure_reference",
        max_candidates: int = 8,
    ) -> HtmlAnalysisResult:
        html = Path(html_path).read_text(encoding="utf-8")
        return self.analyze(
            html=html,
            source_url=source_url,
            source_name=source_name,
            max_candidates=max_candidates,
        )

    def analyze(
        self,
        html: str,
        source_url: str = DEFAULT_SOURCE_URL,
        source_name: str = "naver_shopping_structure_reference",
        max_candidates: int = 8,
    ) -> HtmlAnalysisResult:
        soup = BeautifulSoup(html, "html.parser")
        card_candidates = self._find_card_candidates(soup, max_candidates=max_candidates)
        best_card = card_candidates[0].selector if card_candidates else None
        cards = soup.select(best_card) if best_card else []
        field_candidates = {
            "product_name": self._find_text_field_candidates(cards, max_candidates=max_candidates),
            "price": self._find_price_candidates(cards, max_candidates=max_candidates),
            "seller": self._find_seller_candidates(cards, max_candidates=max_candidates),
            "product_url": self._find_url_candidates(cards, max_candidates=max_candidates),
            "image_url": self._find_image_candidates(cards, max_candidates=max_candidates),
        }
        return HtmlAnalysisResult(
            source_name=source_name,
            source_url=source_url,
            card_candidates=card_candidates,
            field_candidates=field_candidates,
        )

    def build_draft_config(
        self,
        result: HtmlAnalysisResult,
        seller: str = "Naver Shopping",
    ) -> dict[str, Any]:
        """Build a non-approved review draft.

        Confirmed selectors should be copied into `selectors` only after manual
        review and permission verification.
        """

        return {
            "sources": [
                {
                    "name": result.source_name,
                    "collection_method": "approved_html",
                    "seller": seller,
                    "list_urls": [result.source_url],
                    "permission": {
                        "approved": False,
                        "note": "Saved HTML analysis only. Automated collection and reuse are not approved.",
                    },
                    "selectors": {},
                    "attributes": {},
                    "selector_candidates": {
                        "product_card": [asdict(candidate) for candidate in result.card_candidates],
                        **{
                            field: [asdict(candidate) for candidate in candidates]
                            for field, candidates in result.field_candidates.items()
                        },
                    },
                }
            ]
        }

    def write_draft_config(self, result: HtmlAnalysisResult, output_path: str | Path) -> None:
        draft = self.build_draft_config(result)
        Path(output_path).write_text(
            yaml.safe_dump(draft, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )

    def extract_ad_products_file(
        self,
        html_path: str | Path,
        source_url: str = DEFAULT_SOURCE_URL,
        limit: Optional[int] = None,
    ) -> list[ExtractedNaverAdProduct]:
        html = Path(html_path).read_text(encoding="utf-8")
        return self.extract_ad_products(html=html, source_url=source_url, limit=limit)

    def extract_ad_products(
        self,
        html: str,
        source_url: str = DEFAULT_SOURCE_URL,
        limit: Optional[int] = None,
    ) -> list[ExtractedNaverAdProduct]:
        soup = BeautifulSoup(html, "html.parser")
        source_url = self._resolved_source_url(soup, source_url)
        cards = soup.select(NAVER_AD_SELECTORS["product_card"])
        if limit is not None:
            cards = cards[:limit]
        next_data_products = self._next_data_products_by_title(soup)

        extracted: list[ExtractedNaverAdProduct] = []
        for card in cards:
            title_tag = card.select_one(NAVER_AD_SELECTORS["product_name"])
            title = self._text(title_tag)
            if not title:
                continue
            json_product = next_data_products.get(title, {})
            image_url = json_product.get("imageUrl")
            if image_url:
                image_url = urljoin(source_url, str(image_url))
            product_url = self._absolute_attr(title_tag, "href", source_url)
            if not product_url:
                continue

            seller = self._text(card.select_one(NAVER_AD_SELECTORS["seller"]))
            if not seller:
                seller = json_product.get("mallName")

            extracted.append(
                ExtractedNaverAdProduct(
                    product_name=title,
                    product_type="ad",
                    price=self._parse_number(self._text(card.select_one(NAVER_AD_SELECTORS["price"])))
                    or self._parse_number(json_product.get("price")),
                    original_price=self._parse_number(self._text(card.select_one(".price_org_price__2W2CX")))
                    or self._parse_number(json_product.get("listPrice")),
                    shipping_fee=self._parse_shipping_fee(self._text(card.select_one(NAVER_AD_SELECTORS["shipping_fee"])))
                    if self._text(card.select_one(NAVER_AD_SELECTORS["shipping_fee"]))
                    else self._parse_number(json_product.get("dlvryFee")),
                    seller=seller,
                    product_url=product_url,
                    image_url=image_url,
                    source_url=source_url,
                )
            )
        return extracted

    def extract_all_products_file(
        self,
        html_path: str | Path,
        source_url: str = DEFAULT_SOURCE_URL,
        limit: Optional[int] = None,
    ) -> tuple[list[ExtractedNaverAdProduct], NaverExtractionSummary]:
        html = Path(html_path).read_text(encoding="utf-8")
        return self.extract_all_products(html=html, source_url=source_url, limit=limit)

    def extract_all_products(
        self,
        html: str,
        source_url: str = DEFAULT_SOURCE_URL,
        limit: Optional[int] = None,
    ) -> tuple[list[ExtractedNaverAdProduct], NaverExtractionSummary]:
        soup = BeautifulSoup(html, "html.parser")
        source_url = self._resolved_source_url(soup, source_url)
        ad_titles = self._ad_titles_from_dom(soup)
        raw_items = self._next_data_product_items(soup)
        products: list[ExtractedNaverAdProduct] = []
        seen_names: set[str] = set()

        for item in raw_items:
            title = item.get("productTitle") or item.get("productName")
            if not isinstance(title, str) or not title.strip():
                continue
            title = title.strip()
            if title in seen_names:
                continue
            seen_names.add(title)
            product = self._product_from_next_data_item(
                item=item,
                product_type="ad" if title in ad_titles else "organic",
                source_url=source_url,
            )
            products.append(product)
            if limit is not None and len(products) >= limit:
                break

        summary = self._summary(raw_count=len(raw_items), products=products)
        return products, summary

    def write_extracted_products_json(
        self,
        products: list[ExtractedNaverAdProduct],
        output_path: str | Path,
    ) -> None:
        Path(output_path).write_text(
            json.dumps([asdict(product) for product in products], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def write_extraction_result_json(
        self,
        products: list[ExtractedNaverAdProduct],
        summary: NaverExtractionSummary,
        output_path: str | Path,
    ) -> None:
        payload = {
            "summary": asdict(summary),
            "products": [asdict(product) for product in products],
        }
        Path(output_path).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def format_text_report(self, result: HtmlAnalysisResult) -> str:
        lines = [
            f"source_name: {result.source_name}",
            f"source_url: {result.source_url}",
            "permission.approved: false",
            "",
            "Product card selector candidates:",
        ]
        lines.extend(self._format_candidates(result.card_candidates))
        for field, candidates in result.field_candidates.items():
            lines.append("")
            lines.append(f"{field} selector candidates:")
            lines.extend(self._format_candidates(candidates))
        return "\n".join(lines)

    def format_extracted_products(self, products: list[ExtractedNaverAdProduct]) -> str:
        return json.dumps([asdict(product) for product in products], ensure_ascii=False, indent=2)

    def format_extraction_result(
        self,
        products: list[ExtractedNaverAdProduct],
        summary: NaverExtractionSummary,
    ) -> str:
        return json.dumps(
            {"summary": asdict(summary), "products": [asdict(product) for product in products]},
            ensure_ascii=False,
            indent=2,
        )

    def _format_candidates(self, candidates: list[SelectorCandidate]) -> list[str]:
        if not candidates:
            return ["  - none"]
        return [
            "  - selector: {selector} | matches: {matches} | matching_cards: {cards} | samples: {samples}".format(
                selector=candidate.selector,
                matches=candidate.match_count,
                cards=candidate.matching_cards,
                samples=", ".join(candidate.sample_values[:3]),
            )
            for candidate in candidates
        ]

    def _find_card_candidates(self, soup: BeautifulSoup, max_candidates: int) -> list[SelectorCandidate]:
        candidates: dict[str, int] = {}
        for tag in soup.find_all(["div", "li", "section", "article"]):
            for selector in self._selectors_for_tag(tag):
                candidates[selector] = candidates.get(selector, 0) + 1

        scored: list[tuple[int, SelectorCandidate]] = []
        for selector in candidates:
            matched = soup.select(selector)
            if len(matched) < 2:
                continue
            score = sum(self._card_score(tag) for tag in matched[:20])
            if score <= 0:
                continue
            scored.append(
                (
                    score,
                    SelectorCandidate(
                        selector=selector,
                        match_count=len(matched),
                        matching_cards=len(matched),
                        sample_values=[self._short_text(tag) for tag in matched[:3] if self._short_text(tag)],
                    ),
                )
            )
        scored.sort(key=lambda item: (item[0], item[1].matching_cards), reverse=True)
        return [candidate for _, candidate in scored[:max_candidates]]

    def _find_text_field_candidates(self, cards: list[Any], max_candidates: int) -> list[SelectorCandidate]:
        values: dict[str, list[str]] = {}
        for card in cards:
            for tag in card.find_all(["a", "span", "strong", "em", "div"]):
                text = self._clean_text(tag.get_text(" ", strip=True))
                if not self._looks_like_name(text):
                    continue
                for selector in self._selectors_for_tag(tag):
                    values.setdefault(selector, []).append(text)
        return self._rank_field_candidates(cards, values, max_candidates)

    def _find_price_candidates(self, cards: list[Any], max_candidates: int) -> list[SelectorCandidate]:
        values: dict[str, list[str]] = {}
        for card in cards:
            for tag in card.find_all(["span", "strong", "em", "div"]):
                text = self._clean_text(tag.get_text(" ", strip=True))
                if not self._looks_like_price(text):
                    continue
                for selector in self._selectors_for_tag(tag):
                    values.setdefault(selector, []).append(text)
        return self._rank_field_candidates(cards, values, max_candidates)

    def _find_seller_candidates(self, cards: list[Any], max_candidates: int) -> list[SelectorCandidate]:
        values: dict[str, list[str]] = {}
        for card in cards:
            for tag in card.find_all(["a", "span", "strong", "em", "div"]):
                text = self._clean_text(tag.get_text(" ", strip=True))
                if not text or self._looks_like_price(text) or len(text) > 80:
                    continue
                if not self._selector_or_attrs_contain(tag, ["seller", "mall", "store", "shop", "brand"]):
                    continue
                for selector in self._selectors_for_tag(tag):
                    values.setdefault(selector, []).append(text)
        return self._rank_field_candidates(cards, values, max_candidates)

    def _find_url_candidates(self, cards: list[Any], max_candidates: int) -> list[SelectorCandidate]:
        values: dict[str, list[str]] = {}
        for card in cards:
            for tag in card.find_all("a", href=True):
                href = str(tag.get("href") or "").strip()
                if not href or href.startswith("#"):
                    continue
                for selector in self._selectors_for_tag(tag):
                    values.setdefault(selector, []).append(href)
        return self._rank_field_candidates(cards, values, max_candidates)

    def _find_image_candidates(self, cards: list[Any], max_candidates: int) -> list[SelectorCandidate]:
        values: dict[str, list[str]] = {}
        for card in cards:
            for tag in card.find_all(["img", "source"]):
                value = tag.get("src") or tag.get("data-src") or tag.get("srcset")
                if not value:
                    continue
                for selector in self._selectors_for_tag(tag):
                    values.setdefault(selector, []).append(str(value).strip())
        return self._rank_field_candidates(cards, values, max_candidates)

    def _rank_field_candidates(
        self,
        cards: list[Any],
        values: dict[str, list[str]],
        max_candidates: int,
    ) -> list[SelectorCandidate]:
        candidates = [
            SelectorCandidate(
                selector=selector,
                match_count=len(samples),
                matching_cards=sum(1 for card in cards if card.select_one(selector)),
                sample_values=self._unique(samples)[:3],
            )
            for selector, samples in values.items()
        ]
        candidates.sort(key=lambda candidate: (candidate.matching_cards, candidate.match_count), reverse=True)
        return candidates[:max_candidates]

    def _selectors_for_tag(self, tag) -> list[str]:
        selectors: list[str] = []
        for attr, value in sorted(tag.attrs.items()):
            if attr == "class":
                continue
            if attr.startswith("data-") and isinstance(value, str) and value.strip():
                selectors.append(f"[{attr}='{self._escape_attr(value.strip())}']")

        classes = [str(value).strip() for value in tag.get("class", []) if str(value).strip()]
        selectors.extend(f".{self._escape_class(class_name)}" for class_name in classes[:3])
        if tag.name and classes:
            selectors.append(f"{tag.name}.{self._escape_class(classes[0])}")
        if tag.name:
            selectors.append(tag.name)
        return self._unique(selectors)

    def _selector_or_attrs_contain(self, tag, words: list[str]) -> bool:
        haystack_parts = [tag.name or ""]
        for attr, value in tag.attrs.items():
            haystack_parts.append(str(attr))
            haystack_parts.append(" ".join(value) if isinstance(value, list) else str(value))
        haystack = " ".join(haystack_parts).lower()
        return any(word in haystack for word in words)

    def _card_score(self, tag) -> int:
        has_link = bool(tag.find("a", href=True))
        has_image = bool(tag.find(["img", "source"]))
        has_price = self._looks_like_price(tag.get_text(" ", strip=True))
        return sum([has_link, has_image, has_price])

    def _looks_like_name(self, text: str) -> bool:
        if not text or len(text) < 2 or len(text) > 140:
            return False
        if self._looks_like_price(text):
            return False
        return bool(re.search(r"[^\W\d_]", text, re.UNICODE))

    def _looks_like_price(self, text: str) -> bool:
        normalized = text.replace(" ", "")
        return bool(PRICE_RE.search(normalized)) and bool(re.search(r"\d", normalized))

    def _short_text(self, tag) -> str:
        return self._clean_text(tag.get_text(" ", strip=True))[:120]

    def _clean_text(self, value: str) -> str:
        return re.sub(r"\s+", " ", value).strip()

    def _escape_attr(self, value: str) -> str:
        return value.replace("\\", "\\\\").replace("'", "\\'")

    def _escape_class(self, value: str) -> str:
        return re.sub(r"([^A-Za-z0-9_-])", r"\\\1", value)

    def _unique(self, values: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            if value in seen:
                continue
            seen.add(value)
            result.append(value)
        return result

    def _next_data_products_by_title(self, soup: BeautifulSoup) -> dict[str, dict[str, Any]]:
        return {
            str(item.get("productTitle") or item.get("productName")): item
            for item in self._next_data_product_items(soup)
            if item.get("imageUrl") and (item.get("productTitle") or item.get("productName"))
        }

    def _next_data_product_items(self, soup: BeautifulSoup) -> list[dict[str, Any]]:
        payload = self._next_data_payload(soup)
        if payload is None:
            return []

        products: list[dict[str, Any]] = []
        seen_object_ids: set[int] = set()
        for node in self._walk_json(payload):
            if not isinstance(node, dict):
                continue
            item = node.get("item")
            if isinstance(item, dict):
                self._append_next_data_product(products, item, seen_object_ids)
            self._append_next_data_product(products, node, seen_object_ids)
        return products

    def _next_data_payload(self, soup: BeautifulSoup) -> Optional[dict[str, Any]]:
        script = soup.find("script", id="__NEXT_DATA__")
        if not script or not script.string:
            return None
        try:
            payload = json.loads(script.string)
        except json.JSONDecodeError:
            return None
        return payload if isinstance(payload, dict) else None

    def _resolved_source_url(self, soup: BeautifulSoup, source_url: str) -> str:
        if source_url != DEFAULT_SOURCE_URL:
            return source_url
        query = self._next_data_search_query(soup)
        if not query:
            return source_url
        return DEFAULT_SOURCE_URL.format(query=quote(query))

    def _next_data_search_query(self, soup: BeautifulSoup) -> Optional[str]:
        payload = self._next_data_payload(soup)
        if not payload:
            return None
        page_props = payload.get("props", {}).get("pageProps", {})
        search_param = page_props.get("searchParam", {})
        query = search_param.get("query") or search_param.get("origQuery") or search_param.get("adQuery")
        if isinstance(query, str) and query.strip():
            return query.strip()
        return None

    def _append_next_data_product(
        self,
        products: list[dict[str, Any]],
        item: dict[str, Any],
        seen_object_ids: set[int],
    ) -> None:
        object_id = id(item)
        if object_id in seen_object_ids:
            return
        title = item.get("productTitle") or item.get("productName")
        if isinstance(title, str) and title and item.get("imageUrl"):
            seen_object_ids.add(object_id)
            products.append(item)

    def _ad_titles_from_dom(self, soup: BeautifulSoup) -> set[str]:
        titles: set[str] = set()
        for card in soup.select(NAVER_AD_SELECTORS["product_card"]):
            title = self._text(card.select_one(NAVER_AD_SELECTORS["product_name"]))
            if title:
                titles.add(title)
        return titles

    def _product_from_next_data_item(
        self,
        item: dict[str, Any],
        product_type: str,
        source_url: str,
    ) -> ExtractedNaverAdProduct:
        title = str(item.get("productTitle") or item.get("productName")).strip()
        return ExtractedNaverAdProduct(
            product_name=title,
            product_type=product_type,
            price=self._parse_number(item.get("price")),
            original_price=self._parse_number(item.get("listPrice")),
            shipping_fee=self._parse_number(item.get("dlvryFee")),
            seller=self._seller_from_next_data_item(item),
            product_url=self._url_from_next_data_item(item, source_url),
            image_url=urljoin(source_url, str(item.get("imageUrl"))) if item.get("imageUrl") else None,
            source_url=source_url,
        )

    def _seller_from_next_data_item(self, item: dict[str, Any]) -> Optional[str]:
        seller = item.get("mallName")
        if isinstance(seller, str) and seller.strip():
            return seller.strip()
        low_mall_list = item.get("lowMallList")
        if isinstance(low_mall_list, list):
            for mall in low_mall_list:
                if isinstance(mall, dict) and mall.get("name"):
                    return str(mall["name"]).strip()
        return None

    def _url_from_next_data_item(self, item: dict[str, Any], source_url: str) -> Optional[str]:
        for field in ("mallProductUrl", "crUrl", "crUrlMore", "mallPcUrl"):
            value = item.get(field)
            if isinstance(value, str) and value.strip():
                return urljoin(source_url, value.strip())
        return None

    def _summary(self, raw_count: int, products: list[ExtractedNaverAdProduct]) -> NaverExtractionSummary:
        fields = ["product_name", "price", "shipping_fee", "seller", "product_url", "image_url"]
        missing = {
            field: sum(getattr(product, field) in (None, "") for product in products)
            for field in fields
        }
        ad_count = sum(product.product_type == "ad" for product in products)
        return NaverExtractionSummary(
            total_before_dedup=raw_count,
            total_after_dedup=len(products),
            ad_count=ad_count,
            organic_count=len(products) - ad_count,
            duplicate_count=raw_count - len(products),
            missing_fields=missing,
        )

    def _walk_json(self, value: Any):
        yield value
        if isinstance(value, dict):
            for child in value.values():
                yield from self._walk_json(child)
        elif isinstance(value, list):
            for child in value:
                yield from self._walk_json(child)

    def _parse_number(self, value: Optional[str]) -> Optional[float]:
        if value is None:
            return None
        value = str(value)
        normalized = re.sub(r"[^0-9.]", "", value)
        if not normalized:
            return None
        try:
            return float(normalized)
        except ValueError:
            return None

    def _text(self, tag) -> Optional[str]:
        if not tag:
            return None
        text = self._clean_text(tag.get_text(" ", strip=True))
        return text or None

    def _parse_shipping_fee(self, value: Optional[str]) -> Optional[float]:
        if not value:
            return None
        if "무료" in value:
            return 0.0
        return self._parse_number(value)

    def _absolute_attr(self, tag, attr: str, source_url: str) -> Optional[str]:
        if not tag:
            return None
        value = tag.get(attr)
        if not value:
            return None
        return urljoin(source_url, str(value).strip())


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze saved Naver Shopping HTML selector candidates.")
    parser.add_argument("html_path", help="Path to a browser-saved HTML file.")
    parser.add_argument("--source-url", default=DEFAULT_SOURCE_URL)
    parser.add_argument("--source-name", default="naver_shopping_structure_reference")
    parser.add_argument("--output-config", help="Write a non-approved YAML draft config.")
    parser.add_argument("--extract-ad-products", action="store_true", help="Extract confirmed ad product fields.")
    parser.add_argument("--extract-all-products", action="store_true", help="Extract all saved products from __NEXT_DATA__.")
    parser.add_argument("--output-json", help="Write extracted ad products to JSON.")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    analyzer = NaverShoppingHtmlAnalyzer()
    if args.extract_all_products:
        products, summary = analyzer.extract_all_products_file(
            html_path=args.html_path,
            source_url=args.source_url,
            limit=args.limit,
        )
        if args.output_json:
            analyzer.write_extraction_result_json(products, summary, args.output_json)
        print(analyzer.format_extraction_result(products, summary))
        return

    if args.extract_ad_products:
        products = analyzer.extract_ad_products_file(
            html_path=args.html_path,
            source_url=args.source_url,
            limit=args.limit,
        )
        if args.output_json:
            analyzer.write_extracted_products_json(products, args.output_json)
        print(analyzer.format_extracted_products(products))
        return

    result = analyzer.analyze_file(
        html_path=args.html_path,
        source_url=args.source_url,
        source_name=args.source_name,
    )
    if args.output_config:
        analyzer.write_draft_config(result, args.output_config)

    if args.format == "json":
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    else:
        print(analyzer.format_text_report(result))


if __name__ == "__main__":
    main()
