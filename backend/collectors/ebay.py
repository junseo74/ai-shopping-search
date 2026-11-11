import base64
import math
import os
import threading
import time
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


class EbayOAuthError(RuntimeError):
    """Sanitized OAuth failure with status for collection-engine classification."""

    def __init__(self, message: str, http_status: int) -> None:
        super().__init__(message)
        self.http_status = http_status


class EbayBrowseCollector(BaseCollector):
    metadata = CollectorMetadata(
        source_name="ebay_browse",
        platform=PlatformType.SHOPPING_MALL,
        requires_api_key=True,
    )

    def __init__(self, token_transport=None) -> None:
        if load_dotenv:
            load_dotenv()
        self.client_id = os.getenv("EBAY_CLIENT_ID")
        self.client_secret = os.getenv("EBAY_CLIENT_SECRET")
        self.marketplace_id = os.getenv("EBAY_MARKETPLACE_ID", "EBAY_US")
        self._access_token: str | None = None
        self._token_expires_at = 0.0
        self._token_lock = threading.Lock()
        self.token_transport = token_transport

    def collect(self, query: str | None = None, limit: int = 50) -> list[Product]:
        if not query:
            raise ValueError("eBay Browse API collection requires a query.")
        token = self._get_access_token()
        for attempt in range(2):
            try:
                response = requests.get(
                    EBAY_SEARCH_URL,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "X-EBAY-C-MARKETPLACE-ID": self.marketplace_id,
                    },
                    params={"q": query, "limit": min(limit, 200)},
                    timeout=15,
                    allow_redirects=False,
                )
            except requests.RequestException:
                # Requests exceptions may contain credentials, URLs or response bodies.
                raise RuntimeError("eBay Browse API request failed.") from None
            if response.status_code == 401:
                self._invalidate_token(token)
                if attempt == 0:
                    token = self._get_access_token()
                    continue
            if response.status_code != 200:
                raise RuntimeError(
                    f"eBay Browse API request failed (HTTP {response.status_code})."
                ) from None
            break
        try:
            payload = response.json()
        except ValueError:
            raise RuntimeError("eBay Browse API returned invalid JSON.") from None
        if not isinstance(payload, dict):
            raise RuntimeError("eBay Browse API returned an invalid response.")
        return [self._to_product(item) for item in payload.get("itemSummaries", [])]

    def _invalidate_token(self, rejected_token: str) -> None:
        with self._token_lock:
            # Do not evict a newer token another concurrent request already obtained.
            if self._access_token == rejected_token:
                self._access_token = None
                self._token_expires_at = 0.0

    def _get_access_token(self) -> str:
        if not self.client_id or not self.client_secret:
            raise RuntimeError("Missing EBAY_CLIENT_ID or EBAY_CLIENT_SECRET in environment.")

        with self._token_lock:
            if self._access_token and time.monotonic() < self._token_expires_at:
                return self._access_token
            self._access_token = None
            self._token_expires_at = 0.0
            return self._mint_access_token()

    @property
    def token_expires_at(self):
        """Compatibility view of the collector-owned early renewal deadline."""
        return self._token_expires_at or None

    @token_expires_at.setter
    def token_expires_at(self, value):
        # Preserve the desktop collector's writable expiry compatibility surface.
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))
                                  or not math.isfinite(value) or value < 0):
            raise ValueError("Invalid eBay OAuth expiry deadline.")
        with self._token_lock:
            self._token_expires_at = value if value is not None else 0.0

    def _mint_access_token(self) -> str:
        # Called under _token_lock. Both paths validate/cache the same application
        # token; the engine path retains common transport throttling and retries.
        credentials = f"{self.client_id}:{self.client_secret}".encode("utf-8")
        encoded = base64.b64encode(credentials).decode("ascii")
        options = {
            "headers": {"Authorization": f"Basic {encoded}",
                        "Content-Type": "application/x-www-form-urlencoded"},
            "data": {"grant_type": "client_credentials", "scope": EBAY_SCOPE},
        }
        requested_at = time.monotonic()
        if self.token_transport is not None:
            # CollectionError from the shared transport is already sanitized;
            # preserve its category/status/retry_after for diagnostics and resume.
            payload = self.token_transport.post_json(EBAY_TOKEN_URL, **options)
        else:
            try:
                response = requests.post(
                    EBAY_TOKEN_URL, timeout=15, allow_redirects=False, **options)
            except requests.RequestException:
                raise RuntimeError("eBay OAuth token request failed.") from None
            try:
                if response.status_code != 200:
                    raise EbayOAuthError(
                        f"eBay OAuth token request failed (HTTP {response.status_code}).",
                        response.status_code,
                    ) from None
                try:
                    payload = response.json()
                except ValueError:
                    raise RuntimeError("eBay OAuth returned invalid JSON.") from None
            finally:
                response.close()
        if not isinstance(payload, dict):
            raise RuntimeError("eBay OAuth returned an invalid response.")
        access_token = payload.get("access_token")
        if not isinstance(access_token, str) or not access_token or any(
            not 33 <= ord(char) <= 126 for char in access_token
        ):
            raise RuntimeError("eBay OAuth response did not include a valid access token.")
        expires_in = payload.get("expires_in")
        try:
            lifetime = float(expires_in)
        except (TypeError, ValueError, OverflowError):
            raise RuntimeError("eBay OAuth response did not include a valid token lifetime.") from None
        if isinstance(expires_in, bool) or not math.isfinite(lifetime) or lifetime <= 0:
            raise RuntimeError("eBay OAuth response did not include a valid token lifetime.")
        expires_at = requested_at + lifetime - min(60.0, lifetime * 0.1)
        if time.monotonic() >= expires_at:
            raise RuntimeError("eBay OAuth token expired during acquisition.")
        self._access_token = access_token
        self._token_expires_at = expires_at
        return access_token

    def _to_product(self, item: dict[str, Any]) -> Product:
        price = item.get("price") or {}
        image = item.get("image") or {}
        seller = item.get("seller") or {}
        shipping_fee = self._extract_shipping_fee(item)

        return Product(
            product_name=item.get("title"),
            price=self._to_float(price.get("value")),
            shipping_fee=shipping_fee,
            currency=price.get("currency"),
            category=self._extract_category(item),
            seller=seller.get("username"),
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
            currency = (item.get("price") or {}).get("currency")
            if not currency or cost.get("currency") != currency:
                continue
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
        if "refurbished" in normalized:
            return ProductCondition.REFURBISHED
        if "used" in normalized or "pre-owned" in normalized or normalized in ("like new", "very good", "good", "acceptable"):
            return ProductCondition.USED
        if normalized == "new" or normalized.startswith("new "):
            return ProductCondition.NEW
        return ProductCondition.UNKNOWN

    def _to_float(self, value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
