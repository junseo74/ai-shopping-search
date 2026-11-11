"""Three credential-gated official catalog APIs. No live success is implied.

The bounded adapters support pagination for validation. Terms and production
capacity approval are independent of possessing a developer key.
"""
import os
from urllib.parse import quote, urlsplit

from dotenv import load_dotenv

from .base import BaseCollector, CollectorMetadata
from ..models import Product, PlatformType
from collection_engine.contracts import CollectionError, Offer, Page
from collection_engine.transport import HttpTransport
from collection_engine.quality import price_number
from collection_engine.responses import (object_value, rows_value, integer_value,
    provider_id, page_request, next_page_cursor)


class OfficialCatalogCollector(BaseCollector):
    required_keys = ()
    documentation = ""

    def __init__(self, transport=None):
        load_dotenv()
        self.credentials = {key: os.getenv(key) for key in self.required_keys}
        self.transport = transport or HttpTransport()

    @property
    def configured(self):
        return all(value and value.strip() for value in self.credentials.values())

    def collect(self, query=None, limit=3):
        return [offer.product for offer in self.fetch_page(query, None, limit).offers]

    def validate_request(self, query, limit, since):
        if not self.configured:
            raise CollectionError("credentials_missing")
        if not isinstance(query, str) or not query.strip() or type(limit) is not int or not 1 <= limit <= 3:
            raise ValueError("Verification requires a query and limit from 1 to 3")
        # No undocumented updated-since query is sent to these search APIs.
        if since is not None:
            raise CollectionError("server_incremental_not_supported")

    def product(self, name, price, currency, url, image=None, seller=None, category=None, condition="unknown"):
        try:
            parsed = urlsplit(url or "")
            if not isinstance(name, str) or not name.strip() or price is None or parsed.scheme != "https" or not parsed.hostname:
                raise CollectionError("parsing_error")
            price = price_number(price)
            return Product(product_name=name, price=price, currency=currency, product_url=url,
                           image_url=image, seller=seller, category=category, condition=condition,
                           platform=PlatformType.SHOPPING_MALL, data_source=self.metadata.source_name,
                           source_license=self.documentation)
        except (ValueError, TypeError):
            raise CollectionError("parsing_error") from None


class YahooShoppingCollector(OfficialCatalogCollector):
    metadata = CollectorMetadata("yahoo_shopping", PlatformType.SHOPPING_MALL, requires_api_key=True)
    required_keys = ("YAHOO_CLIENT_ID",)
    documentation = "https://developer.yahoo.co.jp/webapi/shopping/v3/itemsearch.html"

    def fetch_page(self, query, cursor, limit, since=None):
        self.validate_request(query, limit, since)
        try:
            start = integer_value(cursor if cursor is not None else "1")
        except CollectionError:
            raise CollectionError("invalid_cursor") from None
        if start < 1 or start + limit > 1000:
            raise CollectionError("pagination_limit")
        body = self.transport.get_json("https://shopping.yahooapis.jp/ShoppingWebService/V3/itemSearch",
            params={"appid": self.credentials["YAHOO_CLIENT_ID"], "query": query, "start": start, "results": limit})
        body = object_value(body)
        rows = rows_value(body.get("hits"), limit)
        total = integer_value(body.get("totalResultsAvailable", 0 if not rows else None))
        offers = []
        for row in rows:
            identity = provider_id(row.get("code"))
            product = self.product(row.get("name"), row.get("price"), "JPY", row.get("url"),
                object_value(row.get("image"), True).get("medium"), object_value(row.get("seller"), True).get("name"),
                object_value(row.get("genreCategory"), True).get("name"),
                row.get("condition") if row.get("condition") in ("new", "used") else "unknown")
            offers.append(Offer(product, identity, identity))
        next_start = start + len(rows)
        more = rows and next_start <= total and next_start + limit <= 1000
        return Page(offers, str(next_start) if more else None)


class RakutenIchibaCollector(OfficialCatalogCollector):
    metadata = CollectorMetadata("rakuten_ichiba", PlatformType.SHOPPING_MALL, requires_api_key=True)
    required_keys = ("RAKUTEN_APPLICATION_ID", "RAKUTEN_ACCESS_KEY")
    documentation = "https://webservice.rakuten.co.jp/documentation/ichiba-item-search"

    def fetch_page(self, query, cursor, limit, since=None):
        self.validate_request(query, limit, since)
        page, size = page_request(cursor, limit, maximum=100)
        body = self.transport.get_json("https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701",
            params={"applicationId": self.credentials["RAKUTEN_APPLICATION_ID"],
                    "accessKey": self.credentials["RAKUTEN_ACCESS_KEY"], "keyword": query,
                    "page": page, "hits": size, "format": "json", "formatVersion": 2})
        body = object_value(body)
        rows = rows_value(body.get("Items"), size)
        page_count = integer_value(body.get("pageCount", 0 if not rows else None))
        offers = []
        for row in rows:
            # formatVersion=2 flattens Item wrappers; tolerate documented v1 shape.
            row = object_value(row.get("Item", row))
            identity = provider_id(row.get("itemCode"))
            images = row.get("mediumImageUrls")
            if images is None:
                images = []
            if not isinstance(images, list):
                raise CollectionError("parsing_error")
            image = images[0] if images else None
            if image is not None and not isinstance(image, (str, dict)):
                raise CollectionError("parsing_error")
            if isinstance(image, dict):
                image = image.get("imageUrl")
            product = self.product(row.get("itemName"), row.get("itemPrice"), "JPY", row.get("itemUrl"),
                                   image, row.get("shopName"), str(row["genreId"]) if row.get("genreId") else None)
            offers.append(Offer(product, identity, identity))
        return Page(offers, next_page_cursor(page, size) if len(rows) == size and page < min(page_count, 100) else None)


class BestBuyProductsCollector(OfficialCatalogCollector):
    metadata = CollectorMetadata("bestbuy_products", PlatformType.SHOPPING_MALL, requires_api_key=True)
    required_keys = ("BESTBUY_API_KEY",)
    documentation = "https://bestbuyapis.github.io/api-documentation/"

    def fetch_page(self, query, cursor, limit, since=None):
        self.validate_request(query, limit, since)
        # Restrict expression input instead of allowing query-language injection.
        if not all(character.isalnum() or character.isspace() or character == "-" for character in query):
            raise ValueError("Best Buy query supports letters, digits, spaces and hyphens")
        page, size = page_request(cursor, limit)
        url = "https://api.bestbuy.com/v1/products(search=" + quote(query.strip(), safe="") + ")"
        body = self.transport.get_json(url, params={"apiKey": self.credentials["BESTBUY_API_KEY"],
            "format": "json", "page": page, "pageSize": size,
            "show": "sku,name,salePrice,url,image,condition,categoryPath"})
        body = object_value(body)
        rows = rows_value(body.get("products"), size)
        page_count = integer_value(body.get("totalPages", 0 if not rows else None))
        offers = []
        for row in rows:
            identity = provider_id(row.get("sku"))
            categories = row.get("categoryPath")
            if categories is None:
                categories = []
            if not isinstance(categories, list) or any(not isinstance(value, dict) for value in categories):
                raise CollectionError("parsing_error")
            product = self.product(row.get("name"), row.get("salePrice"), "USD", row.get("url"),
                row.get("image"), None, categories[-1].get("name") if categories else None,
                "new" if row.get("condition") == "New" else "unknown")
            offers.append(Offer(product, identity, identity))
        return Page(offers, next_page_cursor(page, size) if len(rows) == size and page < page_count else None)
