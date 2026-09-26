import base64
import os
from typing import Any

import requests

from .base import BaseCollector, CollectorMetadata

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency is present in normal runtime.
    load_dotenv = None

try:
    from ..models import PlatformType, Product, ProductCondition
except ImportError:
    from models import PlatformType, Product, ProductCondition


EBAY_SCOPE = "https://api.ebay.com/oauth/api_scope"
EBAY_TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
EBAY_SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"


class EbayBrowseCollector(BaseCollector):
    metadata = CollectorMetadata(
        source_name="ebay_browse",
        platform=PlatformType.SHOPPING_MALL,
        requires_api_key=True,
    )

    def __init__(self) -> None:
        if load_dotenv:
            load_dotenv()
        self.client_id = os.getenv("EBAY_CLIENT_ID")
        self.client_secret = os.getenv("EBAY_CLIENT_SECRET")
        self.marketplace_id = os.getenv("EBAY_MARKETPLACE_ID", "EBAY_US")

    def collect(self, query: str | None = None, limit: int = 50) -> list[Product]:
        if not query:
            raise ValueError("eBay Browse API collection requires a query.")
        token = self._get_access_token()
        response = requests.get(
            EBAY_SEARCH_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "X-EBAY-C-MARKETPLACE-ID": self.marketplace_id,
            },
            params={"q": query, "limit": min(limit, 200)},
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
        return [self._to_product(item) for item in payload.get("itemSummaries", [])]

    def _get_access_token(self) -> str:
        if not self.client_id or not self.client_secret:
            raise RuntimeError("Missing EBAY_CLIENT_ID or EBAY_CLIENT_SECRET in environment.")

        credentials = f"{self.client_id}:{self.client_secret}".encode("utf-8")
        encoded = base64.b64encode(credentials).decode("ascii")
        response = requests.post(
            EBAY_TOKEN_URL,
            headers={
                "Authorization": f"Basic {encoded}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"grant_type": "client_credentials", "scope": EBAY_SCOPE},
            timeout=15,
        )
        response.raise_for_status()
        access_token = response.json().get("access_token")
        if not access_token:
            raise RuntimeError("eBay OAuth response did not include an access token.")
        return access_token

    def _to_product(self, item: dict[str, Any]) -> Product:
        price = item.get("price") or {}
        image = item.get("image") or {}
        seller = item.get("seller") or {}
        shipping_fee = self._extract_shipping_fee(item)

        return Product(
            product_name=item.get("title") or "Untitled eBay item",
            price=self._to_float(price.get("value")),
            shipping_fee=shipping_fee,
            currency=price.get("currency") or "USD",
            category=self._extract_category(item),
            seller=seller.get("username") or "eBay seller",
            platform=PlatformType.SHOPPING_MALL,
            product_url=item.get("itemWebUrl"),
            image_url=image.get("imageUrl"),
            condition=self._map_condition(item.get("condition")),
            region=self._extract_region(item),
            data_source=self.metadata.source_name,
        )

    def _extract_shipping_fee(self, item: dict[str, Any]) -> float | None:
        for option in item.get("shippingOptions", []):
            cost = option.get("shippingCost") or {}
            value = self._to_float(cost.get("value"))
            if value is not None:
                return value
        return None

    def _extract_category(self, item: dict[str, Any]) -> str | None:
        categories = item.get("categories") or []
        if categories:
            return categories[-1].get("categoryName")
        category_path = item.get("categoryPath")
        if isinstance(category_path, str):
            return category_path
        return None

    def _extract_region(self, item: dict[str, Any]) -> str | None:
        location = item.get("itemLocation") or {}
        parts = [location.get("city"), location.get("stateOrProvince"), location.get("country")]
        return ", ".join(part for part in parts if part) or None

    def _map_condition(self, condition: str | None) -> ProductCondition:
        if not condition:
            return ProductCondition.UNKNOWN
        normalized = condition.lower()
        if "new" in normalized:
            return ProductCondition.NEW
        if "used" in normalized or "pre-owned" in normalized:
            return ProductCondition.USED
        if "refurbished" in normalized:
            return ProductCondition.REFURBISHED
        return ProductCondition.UNKNOWN

    def _to_float(self, value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
