import csv
import json
import re
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any, Iterable, Optional
from urllib.parse import urlparse

import requests

try:
    from ..models import PlatformType, Product, ProductCondition
except ImportError:
    from models import PlatformType, Product, ProductCondition


FIELD_ALIASES = {
    "product_name": ["product_name", "name", "title", "\uc0c1\ud488\uba85", "\ubb3c\ud488\uc2dd\ubcc4\uba85", "\uc138\ubd80\ud488\uba85"],
    "price": ["price", "product_price", "sale_price", "\uac00\uaca9", "\ud310\ub9e4\uac00", "\ub0a9\ud488\ub2e8\uac00", "\uacc4\uc57d\ub2e8\uac00"],
    "shipping_fee": ["shipping_fee", "delivery_fee", "\ubc30\uc1a1\ube44"],
    "seller": ["seller", "vendor", "provider", "\ud310\ub9e4\ucc98", "\ud310\ub9e4\uc790", "\uc5c5\uccb4", "\uacf5\uae09\uc5c5\uccb4"],
    "detail_description": ["detail_description", "description", "desc", "\uc124\uba85", "\uc0c1\ud488\uc124\uba85", "\uc138\ubd80\ud488\uba85(\uba85\uce6d)"],
    "product_url": ["product_url", "url", "link", "\uc0c1\ud488URL", "\uc0c1\ud488 URL"],
    "image_url": ["image_url", "image", "\uc0c1\ud488\uc774\ubbf8\uc9c0", "\uc774\ubbf8\uc9c0URL"],
    "category": ["category", "\uce74\ud14c\uace0\ub9ac", "\ubb3c\ud488\ubd84\ub958\uba85"],
}


class ProductFileImporter:
    def load(
        self,
        file_path: Path | str,
        data_source: str,
        source_url: Optional[str] = None,
        source_license: Optional[str] = None,
        source_observed_at: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> list[Product]:
        rows = self._read_rows(file_path)
        products: list[Product] = []
        for row in rows:
            product = self._row_to_product(
                row=row,
                data_source=data_source,
                source_url=source_url,
                source_license=source_license,
                source_observed_at=source_observed_at,
            )
            if product:
                products.append(product)
            if limit and len(products) >= limit:
                break
        return products

    def _read_rows(self, file_path: Path | str) -> list[dict[str, Any]]:
        if self._is_url(str(file_path)):
            response = requests.get(str(file_path), timeout=30)
            response.raise_for_status()
            suffix = Path(urlparse(str(file_path)).path).suffix.lower()
            content = response.text
            if suffix == ".csv":
                return [dict(row) for row in csv.DictReader(StringIO(content))]
            if suffix == ".json":
                return self._json_rows(json.loads(content))
            raise ValueError(f"Unsupported import URL type: {suffix}")

        path = Path(file_path)
        if path.suffix.lower() == ".csv":
            with path.open("r", encoding="utf-8-sig", newline="") as file:
                return [dict(row) for row in csv.DictReader(file)]
        if path.suffix.lower() == ".json":
            with path.open("r", encoding="utf-8") as file:
                return self._json_rows(json.load(file))
        raise ValueError(f"Unsupported import file type: {path.suffix}")

    def _json_rows(self, payload: Any) -> list[dict[str, Any]]:
            if isinstance(payload, dict):
                for key in ("items", "data", "products", "rows"):
                    if isinstance(payload.get(key), list):
                        return [dict(item) for item in payload[key]]
            if isinstance(payload, list):
                return [dict(item) for item in payload]
            raise ValueError("Unsupported JSON import shape.")

    def _is_url(self, value: str) -> bool:
        return value.startswith("http://") or value.startswith("https://")

    def _row_to_product(
        self,
        row: dict[str, Any],
        data_source: str,
        source_url: Optional[str],
        source_license: Optional[str],
        source_observed_at: Optional[datetime],
    ) -> Optional[Product]:
        name = self._get(row, "product_name")
        if not name:
            return None
        return Product(
            product_name=name,
            price=self._to_float(self._get(row, "price")),
            shipping_fee=self._to_float(self._get(row, "shipping_fee")),
            currency="KRW",
            category=self._get(row, "category"),
            seller=self._get(row, "seller"),
            platform=PlatformType.SHOPPING_MALL,
            product_url=self._get(row, "product_url"),
            image_url=self._get(row, "image_url"),
            condition=ProductCondition.UNKNOWN,
            region=None,
            detail_description=self._get(row, "detail_description"),
            source_url=source_url,
            source_license=source_license,
            source_observed_at=source_observed_at,
            collected_at=datetime.now(timezone.utc),
            data_source=data_source,
        )

    def _get(self, row: dict[str, Any], canonical: str) -> Optional[str]:
        for key in FIELD_ALIASES[canonical]:
            if key in row and row[key] not in (None, ""):
                return str(row[key]).strip()
        return None

    def _to_float(self, value: Optional[str]) -> Optional[float]:
        if value is None:
            return None
        normalized = re.sub(r"[^0-9.]", "", str(value))
        if not normalized:
            return None
        try:
            return float(normalized)
        except ValueError:
            return None
