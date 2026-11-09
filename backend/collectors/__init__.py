from .approved_html import ApprovedHtmlProductCollector, HtmlListSiteConfig, HtmlProductListParser, HtmlProductParser
from .base import BaseCollector, CollectorMetadata
from .apple_books import AppleBooksLookupCollector
from .yes24 import Yes24ProductCollector
from .ebay import EbayBrowseCollector
from .elevenst import ElevenstProductCollector
from .shopping_auto import ShoppingAutoCollector, ShoppingSourceConfig, ShoppingSourceFailure
from .test_fixture import TestFixtureCollector

__all__ = [
    "BaseCollector",
    "AppleBooksLookupCollector",
    "Yes24ProductCollector",
    "CollectorMetadata",
    "ApprovedHtmlProductCollector",
    "EbayBrowseCollector",
    "ElevenstProductCollector",
    "HtmlListSiteConfig",
    "HtmlProductListParser",
    "HtmlProductParser",
    "ShoppingAutoCollector",
    "ShoppingSourceConfig",
    "ShoppingSourceFailure",
    "TestFixtureCollector",
]
