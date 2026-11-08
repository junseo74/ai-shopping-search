import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from backend.collectors.official_catalogs import YahooShoppingCollector, RakutenIchibaCollector, BestBuyProductsCollector
from collection_engine.adapters import BackendCollectorAdapter, EbayPagedAdapter, LegacySavedHtmlAdapter
from collection_engine.contracts import CollectionError
from collection_engine.registry import policies


class OfficialCatalogTest(unittest.TestCase):
    def create(self, factory, response):
        transport = Mock()
        transport.get_json.return_value = response
        with patch.dict(os.environ, {key: "synthetic-credential" for key in factory.required_keys}):
            collector = factory(transport=transport)
        return collector, transport

    def test_all_three_missing_credentials_make_no_requests(self):
        for factory in (YahooShoppingCollector, RakutenIchibaCollector, BestBuyProductsCollector):
            with patch.dict(os.environ, {key: "" for key in factory.required_keys}):
                transport = Mock()
                collector = factory(transport)
                with self.assertRaisesRegex(CollectionError, "credentials_missing"):
                    collector.collect("keyboard", 1)
                transport.get_json.assert_not_called()

    def test_yahoo_name_price_seller_and_cursor(self):
        collector, transport = self.create(YahooShoppingCollector, {"totalResultsAvailable": 5, "hits": [{
            "code": "fixture:1", "name": "Synthetic item", "price": 123, "url": "https://store.shopping.yahoo.co.jp/fixture/1.html",
            "seller": {"name": "Fixture seller"}, "condition": "used"}]})
        page = collector.fetch_page("keyboard", None, 1)
        self.assertEqual(page.next_cursor, "2")
        self.assertEqual(page.offers[0].product.currency, "JPY")
        self.assertEqual(page.offers[0].product.price, 123)
        self.assertEqual(page.offers[0].product.seller, "Fixture seller")
        self.assertEqual(transport.get_json.call_args.kwargs["params"]["start"], 1)

    def test_yahoo_documented_pagination_ceiling(self):
        collector, transport = self.create(YahooShoppingCollector, {})
        with self.assertRaisesRegex(CollectionError, "pagination_limit"):
            collector.fetch_page("keyboard", "999", 3)
        transport.get_json.assert_not_called()

    def test_rakuten_v2_price_and_page(self):
        collector, transport = self.create(RakutenIchibaCollector, {"pageCount": 2, "Items": [{
            "itemCode": "fixture:1", "itemName": "Synthetic item", "itemPrice": 450,
            "itemUrl": "https://item.rakuten.co.jp/fixture/1/", "mediumImageUrls": ["https://example.com/image.jpg"]}]})
        page = collector.fetch_page("keyboard", None, 1)
        self.assertEqual(page.next_cursor, "2")
        self.assertEqual(page.offers[0].product.price, 450)
        self.assertIn("accessKey", transport.get_json.call_args.kwargs["params"])

    def test_rakuten_old_wrapper_tolerated_without_manufacturing_fields(self):
        collector, transport = self.create(RakutenIchibaCollector, {"pageCount": 1, "Items": [{"Item": {
            "itemCode": "fixture:1", "itemName": "Synthetic item", "itemPrice": 0,
            "itemUrl": "https://item.rakuten.co.jp/fixture/1/"}}]})
        page = collector.fetch_page("keyboard", None, 1)
        self.assertIsNone(page.next_cursor)
        self.assertEqual(page.offers[0].product.price, 0)
        self.assertIsNone(page.offers[0].product.seller)

    def test_bestbuy_signed_response_url_preserved_and_page(self):
        url = "https://api.bestbuy.com/click/fixture/123/pdp"
        collector, transport = self.create(BestBuyProductsCollector, {"totalPages": 2, "products": [{
            "sku": 123, "name": "Synthetic keyboard", "salePrice": 19.99, "url": url}]})
        page = collector.fetch_page("keyboard", None, 1)
        self.assertEqual(page.next_cursor, "2")
        self.assertEqual(str(page.offers[0].product.product_url), url)
        self.assertEqual(page.offers[0].product.currency, "USD")

    def test_bestbuy_query_injection_rejected(self):
        collector, transport = self.create(BestBuyProductsCollector, {})
        with self.assertRaises(ValueError):
            collector.collect("keyboard)|salePrice<10", 1)
        transport.get_json.assert_not_called()

    def test_missing_required_raw_fields_is_parsing_error(self):
        collector, _ = self.create(YahooShoppingCollector, {"hits": [{"code": "fixture:1"}]})
        with self.assertRaisesRegex(CollectionError, "parsing_error"):
            collector.fetch_page("keyboard", None, 1)

    def test_no_undocumented_updated_since_parameter(self):
        collector, transport = self.create(YahooShoppingCollector, {})
        with self.assertRaisesRegex(CollectionError, "server_incremental_not_supported"):
            collector.fetch_page("keyboard", None, 1, "2026-11-01")
        transport.get_json.assert_not_called()

    def test_ebay_reuses_oauth_and_mapper_and_native_id(self):
        original = Mock(client_id="fixture", client_secret="fixture", marketplace_id="EBAY_US")
        original._get_access_token.return_value = "synthetic-token"
        transport = Mock()
        transport.get_json.return_value = {"total": 3, "itemSummaries": [{
            "itemId": "v1|123|0", "title": "Synthetic item", "price": {"value": "10", "currency": "USD"}}]}
        adapter = EbayPagedAdapter(original, transport)
        first = adapter.fetch_page("keyboard", None, 1)
        adapter.fetch_page("keyboard", first.next_cursor, 1)
        original._get_access_token.assert_called_once()
        self.assertEqual(first.offers[0].product_id, "v1|123|0")
        self.assertEqual(first.next_cursor, "1")
        self.assertEqual(transport.get_json.call_args.kwargs["params"]["offset"], 1)

    def test_registry_denies_unapproved_legacy_routes(self):
        config = policies()
        for source in ("danawa", "musinsa", "kurly", "29cm", "lotteon", "joongna", "elevenst"):
            self.assertFalse(config[source].lookup_allowed)
            self.assertFalse(config[source].bulk_approved)

    def test_saved_html_adapter_never_calls_legacy_network(self):
        html = '<script type="application/ld+json">{"@type":"Product","name":"Synthetic tea","offers":{"price":1000,"priceCurrency":"KRW","url":"https://www.kurly.com/goods/123"}}</script>'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.html"
            path.write_text(html, encoding="utf-8")
            with patch("crawler_engine.engine.CrawlerEngine.render_page", side_effect=AssertionError("network")), patch("crawler_engine.engine.CrawlerEngine.fetch_detail_page", side_effect=AssertionError("network")):
                page = LegacySavedHtmlAdapter("kurly", path).fetch_page("tea", None, 1)
        self.assertEqual(len(page.offers), 1)
        self.assertEqual(page.offers[0].product.price, 1000)
