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


class OfficialCatalogCollector(BaseCollector):
    required_keys = ()
    documentation = ""

    def __init__(self, transport=None):
        load_dotenv()
        self.credentials = {key: os.getenv(key) for key in self.required_keys}
        self.transport = transport or HttpTransport()

    @property
    def configured(self):
        return all(self.credentials.values())

    def collect(self, query=None, limit=3):
        return [offer.product for offer in self.fetch_page(query, None, limit).offers]

    def validate_request(self, query, limit, since):
        if not self.configured:
            raise CollectionError("credentials_missing")
        if not query or not query.strip() or not isinstance(limit, int) or not 1 <= limit <= 3:
            raise ValueError("Verification requires a query and limit from 1 to 3")
        # No undocumented updated-since query is sent to these search APIs.
        if since is not None:
            raise CollectionError("server_incremental_not_supported")

    def product(self, name, price, currency, url, image=None, seller=None, category=None, condition="unknown"):
        parsed = urlsplit(url or "")
        if not name or price is None or parsed.scheme != "https" or not parsed.hostname:
            raise CollectionError("parsing_error")
        try:
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
        start = int(cursor or "1")
        if start < 1 or start + limit > 1000:
            raise CollectionError("pagination_limit")
        body = self.transport.get_json("https://shopping.yahooapis.jp/ShoppingWebService/V3/itemSearch",
            params={"appid": self.credentials["YAHOO_CLIENT_ID"], "query": query, "start": start, "results": limit})
        if "hits" not in body or not isinstance(body["hits"], list):
            raise CollectionError("parsing_error")
        rows = body["hits"]
        offers = []
        for row in rows:
            if not row.get("code"):
                raise CollectionError("parsing_error")
            product = self.product(row.get("name"), row.get("price"), "JPY", row.get("url"),
                (row.get("image") or {}).get("medium"), (row.get("seller") or {}).get("name"),
                (row.get("genreCategory") or {}).get("name"),
                row.get("condition") if row.get("condition") in ("new", "used") else "unknown")
            offers.append(Offer(product, str(row["code"]), str(row["code"])))
        next_start = start + len(rows)
        more = rows and next_start <= int(body.get("totalResultsAvailable", 0)) and next_start + limit <= 1000
        return Page(offers, str(next_start) if more else None)


class RakutenIchibaCollector(OfficialCatalogCollector):
    metadata = CollectorMetadata("rakuten_ichiba", PlatformType.SHOPPING_MALL, requires_api_key=True)
    required_keys = ("RAKUTEN_APPLICATION_ID", "RAKUTEN_ACCESS_KEY")
    documentation = "https://webservice.rakuten.co.jp/documentation/ichiba-item-search"

    def fetch_page(self, query, cursor, limit, since=None):
        self.validate_request(query, limit, since)
        page = int(cursor or "1")
        if not 1 <= page <= 100:
            raise CollectionError("pagination_limit")
        body = self.transport.get_json("https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701",
            params={"applicationId": self.credentials["RAKUTEN_APPLICATION_ID"],
                    "accessKey": self.credentials["RAKUTEN_ACCESS_KEY"], "keyword": query,
                    "page": page, "hits": limit, "format": "json", "formatVersion": 2})
        rows = body.get("Items")
        if not isinstance(rows, list):
            raise CollectionError("parsing_error")
        offers = []
        for row in rows:
            # formatVersion=2 flattens Item wrappers; tolerate documented v1 shape.
            row = row.get("Item", row)
            if not row.get("itemCode"):
                raise CollectionError("parsing_error")
            images = row.get("mediumImageUrls") or []
            image = images[0] if images else None
            if isinstance(image, dict):
                image = image.get("imageUrl")
            product = self.product(row.get("itemName"), row.get("itemPrice"), "JPY", row.get("itemUrl"),
                                   image, row.get("shopName"), str(row["genreId"]) if row.get("genreId") else None)
            offers.append(Offer(product, str(row["itemCode"]), str(row["itemCode"])))
        return Page(offers, str(page + 1) if rows and page < min(int(body.get("pageCount", 0)), 100) else None)


class BestBuyProductsCollector(OfficialCatalogCollector):
    metadata = CollectorMetadata("bestbuy_products", PlatformType.SHOPPING_MALL, requires_api_key=True)
    required_keys = ("BESTBUY_API_KEY",)
    documentation = "https://bestbuyapis.github.io/api-documentation/"

    def fetch_page(self, query, cursor, limit, since=None):
        self.validate_request(query, limit, since)
        # Restrict expression input instead of allowing query-language injection.
        if not all(character.isalnum() or character.isspace() or character == "-" for character in query):
            raise ValueError("Best Buy query supports letters, digits, spaces and hyphens")
        page = int(cursor or "1")
        if page < 1:
            raise CollectionError("pagination_limit")
        url = "https://api.bestbuy.com/v1/products(search=" + quote(query.strip(), safe="") + ")"
        body = self.transport.get_json(url, params={"apiKey": self.credentials["BESTBUY_API_KEY"],
            "format": "json", "page": page, "pageSize": limit,
            "show": "sku,name,salePrice,url,image,condition,categoryPath"})
        rows = body.get("products")
        if not isinstance(rows, list):
            raise CollectionError("parsing_error")
        offers = []
        for row in rows:
            if row.get("sku") is None:
                raise CollectionError("parsing_error")
            categories = row.get("categoryPath") or []
            product = self.product(row.get("name"), row.get("salePrice"), "USD", row.get("url"),
                row.get("image"), None, categories[-1].get("name") if categories else None,
                "new" if row.get("condition") == "New" else "unknown")
            offers.append(Offer(product, str(row["sku"]), str(row["sku"])))
        return Page(offers, str(page + 1) if rows and page < int(body.get("totalPages", 0)) else None)
