"""Compatibility bridges; old collectors are preserved, not rewritten."""
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
import requests
import math

from backend.models import Product, PlatformType
from .contracts import CollectionError, Offer, Page
from .storage import digest
from .quality import price_number, currency_code
from .responses import object_value, rows_value, integer_value, provider_id


class BackendCollectorAdapter:
    """Existing collect() APIs are one-shot; never simulate offset pagination."""
    def __init__(self, collector):
        self.collector = collector
        self.source = collector.metadata.source_name

    def fetch_page(self, query, cursor, limit, since=None):
        if cursor is not None or since is not None:
            raise CollectionError("pagination_or_incremental_not_supported")
        try:
            products = self.collector.collect(query, limit)
        except CollectionError:
            raise
        except requests.Timeout:
            raise CollectionError("timeout") from None
        except requests.HTTPError as error:
            status = error.response.status_code if error.response is not None else None
            category = {401: "authentication_failed", 403: "permission_denied", 429: "rate_limit"}.get(status, "access_error")
            raise CollectionError(category, status) from None
        except requests.RequestException:
            raise CollectionError("access_error") from None
        except (ValueError, TypeError, KeyError, AttributeError):
            raise CollectionError("parsing_error") from None
        offers = []
        for product in products:
            # Preserve query parameters: they may select different product variants.
            parsed = urlsplit(str(product.product_url or ""))
            canonical = urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path, parsed.query, ""))
            identity = digest(canonical)
            basis = "product_url_hash_fallback"
            if self.source == "apple_books_lookup":
                raw = next((row for row in (self.collector.last_response or {}).get("results", [])
                            if row.get("trackViewUrl") == str(product.product_url)), {})
                if raw.get("trackId") is not None:
                    identity, basis = str(raw["trackId"]), "provider_id"
            elif self.source == "yes24_api":
                raw = next((row for row in (self.collector.last_response or {}).get("data", {}).get("items", [])
                            if row.get("link") == str(product.product_url)), {})
                if raw.get("itemId") is not None:
                    identity, basis = str(raw["itemId"]), "provider_id"
            offers.append(Offer(product, identity, identity, basis))
        return Page(offers)


class PagedCollectorAdapter:
    def __init__(self, collector):
        self.collector = collector
        self.source = collector.metadata.source_name

    def fetch_page(self, query, cursor, limit, since=None):
        return self.collector.fetch_page(query, cursor, limit, since)


class EbayPagedAdapter:
    source = "ebay_browse"

    def __init__(self, collector=None, transport=None):
        from backend.collectors.ebay import EbayBrowseCollector
        from .transport import HttpTransport
        self.transport = transport or HttpTransport()
        self.collector = collector or EbayBrowseCollector(token_transport=self.transport)
        self.last_page_projection = []

    @property
    def checkpoint_context(self):
        return {"marketplace_id": self.collector.marketplace_id}

    def fetch_page(self, query, cursor, limit, since=None):
        from backend.collectors.ebay import EBAY_SEARCH_URL
        if since is not None:
            raise CollectionError("server_incremental_not_supported")
        if not self.collector.client_id or not self.collector.client_secret:
            raise CollectionError("credentials_missing")
        try:
            offset = integer_value(cursor if cursor is not None else "0")
        except CollectionError:
            raise CollectionError("invalid_cursor") from None
        if not isinstance(query, str) or not query.strip() or type(limit) is not int or not 1 <= limit <= 200 or not 0 <= offset < 10000:
            raise ValueError("Invalid eBay bounded page request")
        # Preserve eBay's aligned offsets as the remaining item budget shrinks.
        size = math.gcd(offset, limit) if offset else limit
        token = self._get_access_token()
        for attempt in range(2):
            try:
                body = self.transport.get_json(EBAY_SEARCH_URL,
                    headers={"Authorization": "Bearer " + token,
                             "X-EBAY-C-MARKETPLACE-ID": self.collector.marketplace_id},
                    params={"q": query, "limit": size, "offset": offset})
            except CollectionError as error:
                if error.http_status != 401:
                    raise
                self.collector._invalidate_token(token)
                if attempt == 0:
                    token = self._get_access_token()
                    continue
                raise
            break
        body = object_value(body)
        if body.get("errors"):
            raise CollectionError("api_error")
        if "itemSummaries" not in body and body.get("total") != 0:
            raise CollectionError("parsing_error")
        rows = rows_value(body.get("itemSummaries", []), size)
        total = integer_value(body.get("total", 0 if not rows else None))
        offers = []
        self.last_page_projection = []
        for row in rows:
            identity = provider_id(row.get("itemId"))
            price = object_value(row.get("price"))
            if not isinstance(row.get("title"), str) or not row["title"].strip() or price.get("value") is None:
                raise CollectionError("parsing_error")
            # Keep mapper reuse, but never let its historical defaults invent
            # absent currencies or seller names. Normalize numeric strings first.
            normalized = dict(row)
            normalized["price"] = dict(price, value=price_number(price["value"]), currency=currency_code(price.get("currency")))
            if row.get("condition") is not None and not isinstance(row["condition"], str):
                raise CollectionError("parsing_error")
            for field in ("image", "seller", "itemLocation"):
                if field in row:
                    object_value(row[field], True)
            for field in ("categories", "shippingOptions"):
                if field in row:
                    rows_value(row[field], 1000)
            shipping = []
            for option in row.get("shippingOptions", []):
                cost = object_value(option.get("shippingCost"), True)
                if cost:
                    cost = dict(cost)
                    if cost.get("value") is not None:
                        cost["value"] = price_number(cost["value"])
                    if cost.get("currency") is not None:
                        cost["currency"] = currency_code(cost["currency"])
                shipping.append(dict(option, shippingCost=cost))
            if "shippingOptions" in row:
                normalized["shippingOptions"] = shipping
            self.last_page_projection.append({key: row.get(key) for key in ("itemId", "title", "price", "itemWebUrl")})
            try:
                product = self.collector._to_product(normalized)
            except (ValueError, TypeError):
                raise CollectionError("parsing_error") from None
            offers.append(Offer(product, identity, self.collector.marketplace_id + ":" + identity))
        next_offset = offset + len(rows)
        more = rows and next_offset < min(total, 10000)
        return Page(offers, str(next_offset) if more else None)

    def _get_access_token(self):
        # The collector owns expiry and locking; never cache a second stale token here.
        try:
            return self.collector._get_access_token()
        except CollectionError:
            raise
        except Exception as error:
            status = getattr(error, "http_status", None)
            if isinstance(error, requests.HTTPError) and error.response is not None:
                status = error.response.status_code
            category = {401: "authentication_failed", 403: "permission_denied"}.get(status, "oauth_error")
            raise CollectionError(category, status) from None


class LegacySavedHtmlAdapter:
    """Reuse all seven legacy extractors on a provided, legitimately held file.

    No implicit browser, private API, detail request or network fallback. Live
    HTML fetching requires a separate approved source and per-path robots guard.
    """
    def __init__(self, source, path):
        self.source = source
        self.path = Path(path)

    def fetch_page(self, query, cursor, limit, since=None):
        if cursor is not None or since is not None:
            raise CollectionError("pagination_or_incremental_not_supported")
        from crawler_engine.engine import CrawlerEngine
        from crawler_engine.sources import available_sources
        from crawler_engine.models import CrawlRequest
        from crawler_engine.aggregation import aggregate_candidates
        from crawler_engine.normalize import normalize_candidate
        metadata = available_sources()[self.source].metadata
        engine = CrawlerEngine()
        html = self.path.read_text(encoding="utf-8")
        url = available_sources()[self.source].build_search_url(CrawlRequest(query))
        candidates = engine.extract_candidates(html, metadata, limit=limit * 8, query=query)
        candidates = aggregate_candidates(candidates, metadata, url, query=query, include_used=True)
        offers = []
        rejected = 0
        for candidate in candidates[:limit]:
            old = normalize_candidate(candidate, metadata, url)
            if not old:
                rejected += 1
                continue
            product = Product(product_name=old.product_name, price=old.price, currency=old.currency,
                seller=old.seller, condition=old.condition, product_url=old.product_url, image_url=old.image_url,
                platform=PlatformType.SECONDHAND if metadata.used_only else PlatformType.SHOPPING_MALL,
                collected_at=old.collected_at, data_source=self.source)
            identity = digest(str(old.product_url or ""))
            offers.append(Offer(product, identity, identity, "product_url_hash_fallback"))
        return Page(offers, rejected=rejected)
