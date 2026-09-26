from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class PlatformType(str, Enum):
    SHOPPING_MALL = "shopping_mall"
    SECONDHAND = "secondhand"
    GROUP_BUY = "group_buy"
    YOUTUBE_SHOPPING = "youtube_shopping"
    TEST = "test"


class ProductCondition(str, Enum):
    NEW = "new"
    USED = "used"
    REFURBISHED = "refurbished"
    UNKNOWN = "unknown"


class Product(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: Optional[int] = None
    product_name: str = Field(..., min_length=1)
    price: Optional[float] = Field(default=None, ge=0)
    shipping_fee: Optional[float] = Field(default=None, ge=0)
    currency: str = Field(default="KRW", min_length=3, max_length=3)
    category: Optional[str] = None
    seller: Optional[str] = None
    platform: PlatformType
    product_url: Optional[HttpUrl] = None
    image_url: Optional[HttpUrl] = None
    condition: ProductCondition = ProductCondition.UNKNOWN
    region: Optional[str] = None
    detail_description: Optional[str] = None
    source_url: Optional[HttpUrl] = None
    source_license: Optional[str] = None
    source_observed_at: Optional[datetime] = None
    collected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data_source: str = Field(..., min_length=1)


class CollectionRun(BaseModel):
    id: Optional[int] = None
    source_name: str
    platform: PlatformType
    status: str
    product_count: int = 0
    response_time_ms: float = 0
    error_message: Optional[str] = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
