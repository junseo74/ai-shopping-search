"""Documented YES24 API; credential readiness does not mean live verification.

Only on-demand, bounded queries. Terms prohibit building a separate catalog DB.
"""
import os
from urllib.parse import urlsplit

import requests
from dotenv import load_dotenv

from .base import BaseCollector, CollectorMetadata
from collection_engine.contracts import CollectionError
from collection_engine.responses import object_value, rows_value, provider_id
from collection_engine.quality import price_number
try:
    from ..models import PlatformType, Product
except ImportError:
    from models import PlatformType, Product

API_URL = "https://apis.yes24.com/v1/goods/itemList"
TERMS_URL = "https://developers.yes24.com/support/terms"


class Yes24ProductCollector(BaseCollector):
    metadata = CollectorMetadata("yes24_api", PlatformType.SHOPPING_MALL, requires_api_key=True)

    def __init__(self, transport=None):
        self.transport = transport
        self.last_response = None
        load_dotenv()
        self.api_key = os.getenv("YES24_API_KEY")

    def collect(self, query=None, limit=3):
        self.last_response = None
        if not self.api_key:
            raise RuntimeError("Missing YES24_API_KEY in environment; no API request made.")
        if not isinstance(query, str) or not query.strip():
            raise ValueError("YES24 requires a search query.")
        if type(limit) is not int or not 1 <= limit <= 3:
            raise ValueError("YES24 verification supports 1 to 3 products only.")
        options = {"params": {"query": query, "page": 1, "pageSize": limit},
                   "headers": {"X-Api-Key": self.api_key}}
        if self.transport is not None:
            body = self.transport.get_json(API_URL, **options)
        else:
            try:
                response = requests.get(API_URL, timeout=20, allow_redirects=False, **options)
            except requests.RequestException:
                raise RuntimeError("YES24 network error; request details omitted.") from None
            try:
                if response.status_code != 200:
                    raise RuntimeError(f"YES24 API HTTP {response.status_code}; no retry or redirect.")
                try:
                    body = response.json()
                except ValueError:
                    raise ValueError("YES24 returned invalid JSON.") from None
            finally:
                response.close()
        body = object_value(body)
        if body.get("success") is not True:
            if self.transport is not None:
                raise CollectionError("api_error")
            code = str(body.get("errorCode", "unknown"))
            safe = code if code.replace("_", "").isalnum() and self.api_key not in code else "withheld"
            raise RuntimeError(f"YES24 API error code {safe[:80]}")
        rows = rows_value(object_value(body.get("data")).get("items"), 200)
        self.last_response = body
        products, seen = [], set()
        for item in rows:
            identity = provider_id(item.get("itemId"))
            if identity in seen:
                continue
            products.append(self.to_product(item))
            seen.add(identity)
            if len(products) == limit:
                break
        return products

    def to_product(self, item):
        url = item.get("link") or ""
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.hostname != "www.yes24.com":
            raise ValueError("YES24 result lacks an official HTTPS product URL.")
        if not item.get("title") or item.get("salePrice") is None:
            raise ValueError("YES24 result lacks title or salePrice.")
        return Product(product_name=item["title"], price=price_number(item["salePrice"]),
                       original_price=price_number(item.get("shopPrice")), currency="KRW",
                       seller=None, platform=PlatformType.SHOPPING_MALL,
                       product_url=url, image_url=item.get("cover"),
                       category=item.get("goodsType"), condition="unknown",
                       source_url=API_URL, source_license=TERMS_URL,
                       data_source=self.metadata.source_name)
