import os
import re
import xml.etree.ElementTree as ET
from typing import Optional

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


ELEVENST_API_URL = "http://openapi.11st.co.kr/openapi/OpenApiService.tmall"


class ElevenstProductCollector(BaseCollector):
    metadata = CollectorMetadata(
        source_name="elevenst",
        platform=PlatformType.SHOPPING_MALL,
        requires_api_key=True,
    )

    def __init__(self) -> None:
        if load_dotenv:
            load_dotenv()
        self.api_key = os.getenv("ELEVENST_API_KEY")

    def collect(self, query: str | None = None, limit: int = 50) -> list[Product]:
        if not self.api_key:
            raise RuntimeError("Missing ELEVENST_API_KEY in environment.")
        if not query:
            raise ValueError("11st product collection requires a query.")

        response = requests.get(
            ELEVENST_API_URL,
            params={
                "key": self.api_key,
                "apiCode": "ProductSearch",
                "keyword": query,
                "pageNum": 1,
                "pageSize": min(limit, 200),
            },
            timeout=15,
        )
        response.raise_for_status()
        root = ET.fromstring(response.content)
        self._raise_if_error(root)
        return [self._product_from_xml(node) for node in root.findall(".//Product")][:limit]

    def _raise_if_error(self, root: ET.Element) -> None:
        error = root.find(".//Error")
        if error is not None:
            code = self._text(error, "Code") or self._text(error, "code") or "unknown"
            message = self._text(error, "Message") or self._text(error, "message") or ET.tostring(error, encoding="unicode")
            raise RuntimeError(f"11st API error {code}: {message}")

    def _product_from_xml(self, node: ET.Element) -> Product:
        return Product(
            product_name=self._text(node, "ProductName") or "Untitled 11st product",
            price=self._parse_number(self._text(node, "ProductPrice") or self._text(node, "SalePrice")),
            shipping_fee=self._parse_shipping_fee(self._text(node, "Delivery") or self._text(node, "ShipFee")),
            currency="KRW",
            category=None,
            seller=self._text(node, "Seller") or "11st seller",
            platform=PlatformType.SHOPPING_MALL,
            product_url=self._text(node, "ProductDetailUrl") or self._text(node, "DetailPageUrl"),
            image_url=self._text(node, "ImageUrl") or self._text(node, "ProductImage") or self._text(node, "BasicImage"),
            condition=ProductCondition.NEW,
            region=None,
            detail_description=None,
            data_source=self.metadata.source_name,
        )

    def _text(self, node: ET.Element, tag: str) -> Optional[str]:
        found = node.find(tag)
        if found is None or found.text is None:
            return None
        value = found.text.strip()
        return value or None

    def _parse_number(self, value: Optional[str]) -> Optional[float]:
        if not value:
            return None
        normalized = re.sub(r"[^0-9.]", "", value)
        if not normalized:
            return None
        try:
            return float(normalized)
        except ValueError:
            return None

    def _parse_shipping_fee(self, value: Optional[str]) -> Optional[float]:
        if not value:
            return None
        if "\ubb34\ub8cc" in value:
            return 0.0
        return self._parse_number(value)
