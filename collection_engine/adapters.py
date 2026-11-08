"""Compatibility bridges; old collectors are preserved, not rewritten."""
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
import requests

from backend.models import Product, PlatformType
from .contracts import CollectionError, Offer, Page
from .storage import digest


class BackendCollectorAdapter:
    """Existing collect() APIs are one-shot; never simulate offset pagination."""
    def __init__(self, collector):
        self.collector = collector
        self.source = collector.metadata.source_name

    def fetch_page(self, query, cursor, limit, since=None):
        if cursor is not None or since is not None:
            raise CollectionError("pagination_or_incremental_not_supported")
        offers = []
        for product in self.collector.collect(query, limit):
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
        self.collector = collector or EbayBrowseCollector()
        self.transport = transport or HttpTransport()
        self._token = None
        self.last_page_projection = []

    def fetch_page(self, query, cursor, limit, since=None):
        from backend.collectors.ebay import EBAY_SEARCH_URL
        if since is not None:
            raise CollectionError("server_incremental_not_supported")
        if not self.collector.client_id or not self.collector.client_secret:
            raise CollectionError("credentials_missing")
        offset = int(cursor or "0")
        if not query or not 1 <= limit <= 200 or not 0 <= offset < 10000:
            raise ValueError("Invalid eBay bounded page request")
        if self._token is None:
            try:
                self._token = self.collector._get_access_token()
            except requests.HTTPError as error:
                status = error.response.status_code if error.response is not None else None
                category = {401: "authentication_failed", 403: "permission_denied"}.get(status, "oauth_error")
                raise CollectionError(category, status) from None
            except Exception:
                raise CollectionError("oauth_error") from None
        body = self.transport.get_json(EBAY_SEARCH_URL,
            headers={"Authorization": "Bearer " + self._token,
                     "X-EBAY-C-MARKETPLACE-ID": self.collector.marketplace_id},
            params={"q": query, "limit": limit, "offset": offset})
        rows = body.get("itemSummaries", [])
        if not isinstance(rows, list):
            raise CollectionError("parsing_error")
        offers = []
        self.last_page_projection = []
        for row in rows:
            if not row.get("itemId") or not row.get("title") or (row.get("price") or {}).get("value") is None:
                raise CollectionError("parsing_error")
            self.last_page_projection.append({key: row.get(key) for key in ("itemId", "title", "price", "itemWebUrl")})
            product = self.collector._to_product(row)
            offers.append(Offer(product, str(row["itemId"]), self.collector.marketplace_id + ":" + str(row["itemId"])))
        next_offset = offset + len(rows)
        more = rows and next_offset < min(int(body.get("total", 0)), 10000)
        return Page(offers, str(next_offset) if more else None)


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
