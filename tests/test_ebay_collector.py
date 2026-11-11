import base64
import io
import json
import os
import traceback
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

import requests

from backend.collectors import EbayBrowseCollector
from backend.collectors.ebay import EBAY_SCOPE, EBAY_SEARCH_URL, EBAY_TOKEN_URL
from backend.models import ProductCondition


class EbayBrowseCollectorTest(unittest.TestCase):
    def test_missing_credentials_does_not_return_fake_products(self):
        with patch.dict(os.environ, {"EBAY_CLIENT_ID": "", "EBAY_CLIENT_SECRET": ""}, clear=False):
            collector = EbayBrowseCollector()
            with self.assertRaises(RuntimeError):
                collector.collect(query="phone", limit=1)

    def test_maps_item_summary_to_product(self):
        collector = EbayBrowseCollector()
        product = collector._to_product(
            {
                "title": "Example Phone",
                "price": {"value": "199.99", "currency": "USD"},
                "shippingOptions": [{"shippingCost": {"value": "5.00", "currency": "USD"}}],
                "seller": {"username": "example-seller"},
                "itemWebUrl": "https://www.ebay.com/itm/123",
                "image": {"imageUrl": "https://i.ebayimg.com/images/example.jpg"},
                "condition": "Used",
                "categories": [{"categoryName": "Cell Phones"}],
                "itemLocation": {"city": "San Jose", "country": "US"},
            }
        )

        self.assertEqual(product.product_name, "Example Phone")
        self.assertEqual(product.price, 199.99)
        self.assertEqual(product.shipping_fee, 5.0)
        self.assertEqual(product.seller, "example-seller")
        self.assertEqual(product.condition, ProductCondition.USED)
        self.assertEqual(product.data_source, "ebay_browse")


class EbayOAuthTest(unittest.TestCase):
    """Synthetic credentials only; every HTTP call is mocked, never sent to eBay."""

    def setUp(self):
        for patcher in (
            patch("backend.collectors.ebay.load_dotenv", None),
            patch.dict(os.environ, {
                "EBAY_CLIENT_ID": "synthetic-client-id",
                "EBAY_CLIENT_SECRET": "synthetic-client-secret",
                "EBAY_ACCESS_TOKEN": "synthetic-legacy-token",
                "EBAY_MARKETPLACE_ID": "EBAY_GB",
            }),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.collector = EbayBrowseCollector()
        self.post = self.enterContext(patch("backend.collectors.ebay.requests.post"))
        self.get = self.enterContext(patch("backend.collectors.ebay.requests.get"))
        self.clock = self.enterContext(patch("backend.collectors.ebay.time.monotonic", return_value=100.0))
        self.post.return_value = self.response({"access_token": "synthetic-token", "expires_in": 7200})
        self.get.return_value = self.response({"itemSummaries": []})

    @staticmethod
    def response(payload, status=200):
        response = requests.Response()
        response.status_code = status
        response._content = json.dumps(payload).encode("utf-8")
        return response

    def test_uses_client_credentials_grant_without_manual_token(self):
        self.assertEqual(self.collector.collect("phone", 250), [])
        self.post.assert_called_once_with(
            EBAY_TOKEN_URL,
            headers={
                "Authorization": "Basic " + base64.b64encode(b"synthetic-client-id:synthetic-client-secret").decode(),
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"grant_type": "client_credentials", "scope": EBAY_SCOPE},
            timeout=15, allow_redirects=False,
        )
        self.get.assert_called_once_with(
            EBAY_SEARCH_URL,
            headers={"Authorization": "Bearer synthetic-token", "X-EBAY-C-MARKETPLACE-ID": "EBAY_GB"},
            params={"q": "phone", "limit": 200}, timeout=15, allow_redirects=False,
        )

    def test_reuses_cached_token_across_collections(self):
        self.collector.collect("phone", 1)
        self.collector.collect("laptop", 2)
        self.assertEqual(self.post.call_count, 1)
        self.assertEqual(self.get.call_count, 2)

    def test_refreshes_before_expiry_and_at_safety_boundary(self):
        self.collector._get_access_token()
        self.clock.return_value = 7239.0
        self.collector._get_access_token()
        self.assertEqual(self.post.call_count, 1)
        self.clock.return_value = 7240.0
        self.collector._get_access_token()
        self.assertEqual(self.post.call_count, 2)

    def test_scales_safety_margin_for_short_lifetime(self):
        self.post.return_value = self.response({"access_token": "synthetic-short-token", "expires_in": 10})
        self.collector._get_access_token()
        self.assertEqual(self.collector._token_expires_at, 109.0)
        self.clock.return_value = 108.0
        self.collector._get_access_token()
        self.assertEqual(self.post.call_count, 1)

    def test_new_instance_does_not_share_another_clients_token(self):
        self.collector._get_access_token()
        other = EbayBrowseCollector()
        other._get_access_token()
        self.assertEqual(self.post.call_count, 2)

    def test_concurrent_token_requests_only_mint_once(self):
        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(lambda _: self.collector._get_access_token(), range(16)))
        self.assertEqual(len(set(results)), 1)
        self.assertEqual(self.post.call_count, 1)

    def test_401_refreshes_once_then_returns_existing_product_contract(self):
        self.post.side_effect = [self.response({"access_token": token, "expires_in": 7200})
                                 for token in ["synthetic-old-token", "synthetic-new-token"]]
        self.get.side_effect = [self.response({}, 401), self.response({"itemSummaries": [
            {"title": "Synthetic phone", "price": {"value": "12.50", "currency": "GBP"}}
        ]})]
        products = self.collector.collect("phone", 1)
        self.assertEqual(products[0].price, 12.5)
        self.assertEqual(products[0].currency, "GBP")
        self.assertEqual(products[0].data_source, "ebay_browse")
        self.assertEqual(self.post.call_count, 2)
        self.assertEqual(self.get.call_count, 2)
        self.assertEqual(self.get.call_args.kwargs["headers"]["Authorization"], "Bearer synthetic-new-token")

    def test_repeated_401_stops_after_one_retry_and_clears_rejected_token(self):
        self.get.return_value = self.response({"message": "synthetic-private-response"}, 401)
        with self.assertRaisesRegex(RuntimeError, "HTTP 401") as error:
            self.collector.collect("phone", 1)
        self.assertNotIn("synthetic-private-response", str(error.exception))
        self.assertEqual(self.post.call_count, 2)
        self.assertEqual(self.get.call_count, 2)
        self.assertIsNone(self.collector._access_token)

    def test_permission_rate_limit_server_and_redirect_errors_are_not_retried(self):
        for status in [400, 403, 429, 500, 503, 302]:
            with self.subTest(status=status):
                self.get.reset_mock()
                self.get.return_value = self.response({}, status)
                with self.assertRaisesRegex(RuntimeError, f"HTTP {status}"):
                    self.collector.collect("phone", 1)
                self.get.assert_called_once()
        self.post.assert_called_once()

    def test_old_401_does_not_invalidate_newer_token(self):
        self.collector._get_access_token()
        self.collector._invalidate_token("synthetic-older-token")
        self.collector._get_access_token()
        self.post.assert_called_once()

    def test_failed_refresh_does_not_retry_search_or_reuse_old_token(self):
        self.post.side_effect = [self.response({"access_token": "synthetic-token", "expires_in": 7200}),
                                 self.response({"error": "synthetic-client-secret"}, 401)]
        self.get.return_value = self.response({}, 401)
        with self.assertRaisesRegex(RuntimeError, "OAuth token request failed"):
            self.collector.collect("phone", 1)
        self.assertEqual(self.get.call_count, 1)
        self.assertEqual(self.post.call_count, 2)
        self.assertIsNone(self.collector._access_token)

    def test_missing_credentials_fail_without_http_even_with_legacy_token(self):
        for client_id, secret in [(None, None), ("synthetic-id", None), (None, "synthetic-secret")]:
            with self.subTest(case=bool(client_id)):
                self.collector.client_id, self.collector.client_secret = client_id, secret
                with self.assertRaisesRegex(RuntimeError, "Missing EBAY_CLIENT_ID"):
                    self.collector.collect("phone", 1)
        self.post.assert_not_called()
        self.get.assert_not_called()

    def test_missing_query_still_fails_before_authentication(self):
        with self.assertRaises(ValueError):
            self.collector.collect()
        self.post.assert_not_called()
        self.get.assert_not_called()

    def test_invalid_token_lifetimes_are_not_cached(self):
        for lifetime in [None, "", "bad", 0, -1, float("inf"), float("nan"), True, {}, []]:
            with self.subTest(lifetime_type=type(lifetime).__name__):
                self.post.return_value = self.response({"access_token": "synthetic-token", "expires_in": lifetime})
                with self.assertRaisesRegex(RuntimeError, "valid token lifetime"):
                    self.collector._get_access_token()
                self.assertIsNone(self.collector._access_token)

    def test_invalid_token_values_are_not_cached(self):
        for token in [None, "", 1, {}, "synthetic\r\nheader", "synthetic token"]:
            with self.subTest(token_type=type(token).__name__):
                self.post.return_value = self.response({"access_token": token, "expires_in": 7200})
                with self.assertRaisesRegex(RuntimeError, "valid access token"):
                    self.collector._get_access_token()
                self.assertIsNone(self.collector._access_token)

    def test_slow_acquisition_cannot_cache_already_expired_token(self):
        self.clock.side_effect = [100.0, 7301.0]
        with self.assertRaisesRegex(RuntimeError, "expired during acquisition"):
            self.collector._get_access_token()
        self.assertIsNone(self.collector._access_token)

    def test_oauth_http_and_network_errors_are_sanitized_without_retries(self):
        for failure in [self.response({"error": "synthetic-client-secret"}, 400),
                        requests.Timeout("synthetic-client-secret"),
                        requests.ConnectionError("synthetic-client-secret")]:
            with self.subTest(failure_type=type(failure).__name__):
                self.post.reset_mock()
                self.post.side_effect = failure if isinstance(failure, Exception) else None
                self.post.return_value = failure
                with self.assertRaises(RuntimeError) as error:
                    self.collector._get_access_token()
                self.assertNotIn("synthetic-client-secret", str(error.exception))
                self.post.assert_called_once()

    def test_browse_timeout_is_sanitized_and_not_retried(self):
        self.get.side_effect = requests.Timeout("synthetic-private-token")
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr), self.assertNoLogs():
            try:
                self.collector.collect("phone", 1)
            except RuntimeError as error:
                rendered = "".join(traceback.format_exception(error))
            else:
                self.fail("Expected sanitized error")
        self.assertNotIn("synthetic-private-token", rendered)
        self.assertEqual(stdout.getvalue() + stderr.getvalue(), "")
        self.get.assert_called_once()
        self.post.assert_called_once()

    def test_invalid_json_and_schema_are_sanitized(self):
        for target in [self.post, self.get]:
            with self.subTest(endpoint="oauth" if target is self.post else "browse"):
                response = requests.Response()
                response.status_code = 200
                response._content = b"synthetic-private-non-json"
                target.return_value = response
                with self.assertRaisesRegex(RuntimeError, "invalid JSON") as error:
                    self.collector.collect("phone", 1)
                self.assertNotIn("synthetic-private-non-json", str(error.exception))
                self.post.return_value = self.response({"access_token": "synthetic-token", "expires_in": 7200})
        self.collector._invalidate_token("synthetic-token")
        self.post.return_value = self.response([])
        with self.assertRaisesRegex(RuntimeError, "invalid response"):
            self.collector._get_access_token()

    def test_dotenv_load_keeps_environment_override_behavior(self):
        with patch("backend.collectors.ebay.load_dotenv") as loader:
            EbayBrowseCollector()
        loader.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
