import os
import unittest
from unittest.mock import Mock, patch

from backend.collectors.apple_books import AppleBooksLookupCollector, robots_allows
from backend.collectors.yes24 import Yes24ProductCollector
from backend.main import build_collectors, is_collector_configured


class PublicApiGuardTest(unittest.TestCase):
    def test_apple_exact_path_and_other_bot_group(self):
        rules = "User-agent: *\nDisallow: /search*\nDisallow: /*/lookup?\nUser-agent: Googlebot\nDisallow: /\n"
        self.assertTrue(robots_allows(rules, "https://itunes.apple.com/lookup?isbn=9780316069359"))
        self.assertFalse(robots_allows(rules, "https://itunes.apple.com/search?term=book"))
        self.assertFalse(robots_allows(rules, "https://itunes.apple.com/us/lookup?isbn=123"))

    def test_longest_rule_and_allow_tie(self):
        rules = "User-agent: *\nDisallow: /\nAllow: /lookup\nDisallow: /lookup/private\n"
        self.assertTrue(robots_allows(rules, "https://itunes.apple.com/lookup?isbn=123"))
        self.assertFalse(robots_allows(rules, "https://itunes.apple.com/lookup/private"))
        self.assertTrue(robots_allows("User-agent: *\nDisallow: /lookup\nAllow: /lookup", "https://itunes.apple.com/lookup"))

    def test_merge_groups_and_specific_agent(self):
        rules = "User-agent: *\nDisallow: /lookup\nUser-agent: *\nDisallow: /search\n"
        self.assertFalse(robots_allows(rules, "https://itunes.apple.com/search"))
        self.assertFalse(robots_allows(rules, "https://itunes.apple.com/lookup"))
        rules += "User-agent: AIShoppingSearchIntegration\nAllow: /\n"
        self.assertTrue(robots_allows(rules, "https://itunes.apple.com/lookup"))

    @patch("backend.collectors.apple_books.requests.get")
    def test_policy_failure_stops_before_product_request(self, get):
        get.return_value = Mock(status_code=403)
        with self.assertRaisesRegex(RuntimeError, "policy unavailable"):
            AppleBooksLookupCollector().collect("9780316069359", limit=1)
        self.assertEqual(get.call_count, 1)

    @patch("backend.collectors.apple_books.requests.get")
    def test_disallowed_lookup_stops_before_product_request(self, get):
        get.return_value = Mock(status_code=200, text="User-agent: *\nDisallow: /lookup")
        with self.assertRaisesRegex(RuntimeError, "disallows"):
            AppleBooksLookupCollector().collect("9780316069359", limit=1)
        self.assertEqual(get.call_count, 1)

    @patch("backend.collectors.apple_books.requests.get")
    def test_text_search_and_bulk_request_rejected_without_http(self, get):
        collector = AppleBooksLookupCollector()
        for query, limit in [("search book", 1), ("9780316069359", 100)]:
            with self.assertRaises(ValueError):
                collector.collect(query, limit)
        get.assert_not_called()

    @patch("backend.collectors.apple_books.time.sleep")
    @patch("backend.collectors.apple_books.requests.get")
    def test_ebook_mapping_deduplication_and_safe_requests(self, get, sleep):
        item = {"trackId": 123, "trackName": "Fixture book", "price": 0,
                "currency": "USD", "trackViewUrl": "https://books.apple.com/us/book/id123", "kind": "ebook"}
        get.side_effect = [Mock(status_code=200, text="User-agent: *\nDisallow: /search*"),
                           Mock(status_code=200, json=lambda: {"results": [item, item]})]
        products = AppleBooksLookupCollector().collect("9780316069359", 3)
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].price, 0)
        self.assertIsNone(products[0].seller)
        self.assertTrue(all(call.kwargs["allow_redirects"] is False for call in get.call_args_list))
        self.assertTrue(sleep.called)

    def test_missing_price_or_foreign_product_url_rejected(self):
        collector = AppleBooksLookupCollector()
        for item in [{"trackName": "Fixture", "trackViewUrl": "https://books.apple.com/us/book/id123"},
                     {"trackName": "Fixture", "price": 1, "currency": "USD", "trackViewUrl": "https://example.com/book"}]:
            with self.assertRaises(ValueError):
                collector.to_product(item)


class Yes24ReadinessTest(unittest.TestCase):
    @patch("backend.collectors.yes24.requests.get")
    def test_missing_key_stops_without_network(self, get):
        with patch.dict(os.environ, {"YES24_API_KEY": ""}):
            collector = Yes24ProductCollector()
            with self.assertRaisesRegex(RuntimeError, "Missing YES24_API_KEY"):
                collector.collect("book", 1)
            self.assertFalse(is_collector_configured(collector))
        get.assert_not_called()

    @patch("backend.collectors.yes24.requests.get")
    def test_auth_failure_omits_key_and_no_retry(self, get):
        get.return_value = Mock(status_code=401)
        with patch.dict(os.environ, {"YES24_API_KEY": "fixture-secret"}):
            with self.assertRaisesRegex(RuntimeError, "HTTP 401") as raised:
                Yes24ProductCollector().collect("book", 1)
        self.assertNotIn("fixture-secret", str(raised.exception))
        self.assertEqual(get.call_count, 1)
        self.assertEqual(get.call_args.kwargs["headers"], {"X-Api-Key": "fixture-secret"})
        self.assertFalse(get.call_args.kwargs["allow_redirects"])

    @patch("backend.collectors.yes24.requests.get")
    def test_maps_documented_price_and_deduplicates(self, get):
        item = {"itemId": 123, "title": "Fixture book", "salePrice": 10000,
                "shopPrice": 11000, "link": "https://www.yes24.com/product/goods/123"}
        get.return_value = Mock(status_code=200, json=lambda: {"success": True, "data": {"items": [item, item]}})
        with patch.dict(os.environ, {"YES24_API_KEY": "fixture-secret"}):
            products = Yes24ProductCollector().collect("book", 3)
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].price, 10000)
        self.assertEqual(products[0].currency, "KRW")
        self.assertIsNone(products[0].seller)

    def test_sources_registered_but_readiness_is_not_live_success(self):
        collectors = build_collectors()
        self.assertIn("apple_books_lookup", collectors)
        self.assertIn("yes24_api", collectors)
        self.assertIn("ebay_browse", collectors)
        self.assertIn("elevenst", collectors)


if __name__ == "__main__":
    unittest.main()
