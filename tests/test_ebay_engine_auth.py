"""Offline authentication regression tests through the unified eBay adapter."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import requests

from backend.collectors.ebay import EbayBrowseCollector, EBAY_SEARCH_URL
from collection_engine.adapters import EbayPagedAdapter
from collection_engine.contracts import CollectionError, SourcePolicy, utc_now
from collection_engine.runner import CollectionRunner
from collection_engine.storage import FileState, JsonlSink
from collection_engine.transport import HttpTransport


class EbayEngineAuthTest(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch("backend.collectors.ebay.load_dotenv", None))
        self.enterContext(patch.dict(os.environ, {
            "EBAY_CLIENT_ID": "synthetic-unified-client",
            "EBAY_CLIENT_SECRET": "synthetic-unified-secret",
            "EBAY_MARKETPLACE_ID": "EBAY_US",
        }))
        self.clock = self.enterContext(patch("backend.collectors.ebay.time.monotonic", return_value=100.0))
        self.post = self.enterContext(patch("backend.collectors.ebay.requests.post"))
        self.post.return_value = self.token("synthetic-unified-token")
        self.collector = EbayBrowseCollector()
        self.session = Mock()
        self.session.get.return_value = self.page(1)
        self.transport = HttpTransport(session=self.session, sleep=Mock(), clock=lambda: 100.0, jitter=lambda: 0)
        self.adapter = EbayPagedAdapter(self.collector, self.transport)
        # An unexpected real Requests path must fail before opening a socket.
        self.enterContext(patch("requests.sessions.Session.request", side_effect=AssertionError("External HTTP forbidden")))

    @staticmethod
    def response(body, status=200):
        response = requests.Response()
        response.status_code = status
        response._content = json.dumps(body).encode("utf-8")
        return response

    def token(self, value):
        return self.response({"access_token": value, "expires_in": 7200})

    def page(self, item_id, total=2):
        return self.response({"total": total, "itemSummaries": [{
            "itemId": str(item_id), "title": "Synthetic engine item",
            "price": {"value": "10.00", "currency": "USD"},
            "itemWebUrl": "https://www.ebay.com/itm/" + str(item_id),
            "seller": {"username": "synthetic-seller"},
        }]})

    def test_pages_share_collector_cache_and_preserve_offsets_and_identity(self):
        self.session.get.side_effect = [self.page(1), self.page(2)]
        first = self.adapter.fetch_page("phone", None, 1)
        second = self.adapter.fetch_page("phone", first.next_cursor, 1)
        self.assertEqual(first.next_cursor, "1")
        self.assertIsNone(second.next_cursor)
        self.assertEqual(first.offers[0].offer_id, "EBAY_US:1")
        self.assertEqual(first.offers[0].product.price, 10.0)
        self.assertEqual(first.offers[0].product.data_source, "ebay_browse")
        self.assertEqual(self.adapter.last_page_projection[0]["itemId"], "2")
        self.assertEqual([c.kwargs["params"]["offset"] for c in self.session.get.call_args_list], [0, 1])
        self.post.assert_called_once()
        self.assertEqual(self.transport.request_count, 2)

    def test_expiry_between_pages_renews_instead_of_using_adapter_stale_token(self):
        self.post.side_effect = [self.token("synthetic-old"), self.token("synthetic-new")]
        self.adapter.fetch_page("phone", None, 1)
        self.clock.return_value = 7240.0
        self.adapter.fetch_page("phone", "1", 1)
        self.assertEqual(self.post.call_count, 2)
        self.assertEqual(self.session.get.call_args.kwargs["headers"]["Authorization"], "Bearer synthetic-new")

    def test_401_reacquires_once_and_repeats_same_bounded_page(self):
        self.post.side_effect = [self.token("synthetic-old"), self.token("synthetic-new")]
        self.session.get.side_effect = [self.response({}, 401), self.page(5, total=10)]
        page = self.adapter.fetch_page("phone", "4", 1)
        calls = self.session.get.call_args_list
        self.assertEqual(calls[0].kwargs["params"], calls[1].kwargs["params"])
        self.assertEqual(calls[1].kwargs["params"], {"q": "phone", "limit": 1, "offset": 4})
        self.assertEqual(calls[1].kwargs["headers"]["Authorization"], "Bearer synthetic-new")
        self.assertEqual(page.next_cursor, "5")
        self.assertEqual(self.post.call_count, 2)
        self.assertEqual(self.transport.request_count, 2)
        self.assertFalse(calls[1].kwargs["allow_redirects"])
        self.assertEqual(calls[1].args[0], EBAY_SEARCH_URL)

    def test_repeated_401_stops_and_invalidates_second_token(self):
        self.session.get.return_value = self.response({"private": "synthetic-unified-secret"}, 401)
        with self.assertRaises(CollectionError) as error:
            self.adapter.fetch_page("phone", None, 1)
        self.assertEqual(error.exception.category, "authentication_failed")
        self.assertEqual(error.exception.http_status, 401)
        self.assertEqual(self.transport.request_count, 2)
        self.assertEqual(self.post.call_count, 2)
        self.assertIsNone(self.collector._access_token)
        self.assertNotIn("synthetic-unified-secret", str(error.exception))

    def test_failed_reissue_preserves_oauth_status_and_does_not_repeat_page(self):
        self.post.side_effect = [self.token("synthetic-first"), self.response({"private": "synthetic-unified-secret"}, 403)]
        self.session.get.return_value = self.response({}, 401)
        with self.assertRaises(CollectionError) as error:
            self.adapter.fetch_page("phone", None, 1)
        self.assertEqual(error.exception.category, "permission_denied")
        self.assertEqual(error.exception.http_status, 403)
        self.assertEqual(self.transport.request_count, 1)
        self.assertEqual(self.post.call_count, 2)
        self.assertNotIn("synthetic-unified-secret", str(error.exception))

    def test_initial_oauth_http_status_categories_are_preserved(self):
        for status, category in [(401, "authentication_failed"), (403, "permission_denied"), (500, "oauth_error")]:
            with self.subTest(status=status):
                self.post.return_value = self.response({"private": "synthetic-unified-secret"}, status)
                with self.assertRaises(CollectionError) as error:
                    self.adapter.fetch_page("phone", None, 1)
                self.assertEqual(error.exception.category, category)
                self.assertEqual(error.exception.http_status, status)
                self.assertNotIn("synthetic-unified-secret", str(error.exception))
        self.session.get.assert_not_called()

    def test_oauth_network_error_is_sanitized_and_does_not_fetch_page(self):
        self.post.side_effect = requests.Timeout("synthetic-unified-secret")
        with self.assertRaises(CollectionError) as error:
            self.adapter.fetch_page("phone", None, 1)
        self.assertEqual(error.exception.category, "oauth_error")
        self.assertNotIn("synthetic-unified-secret", str(error.exception))
        self.session.get.assert_not_called()
        self.post.assert_called_once()

    def test_permission_and_redirect_failures_do_not_trigger_auth_refresh(self):
        for status in [403, 302]:
            with self.subTest(status=status):
                self.session.get.reset_mock()
                self.session.get.return_value = self.response({}, status)
                with self.assertRaises(CollectionError) as error:
                    self.adapter.fetch_page("phone", None, 1)
                self.assertEqual(error.exception.http_status, status)
                self.session.get.assert_called_once()
        self.post.assert_called_once()

    def test_existing_rate_limit_backoff_uses_same_token(self):
        self.session.get.side_effect = [self.response({}, 429), self.page(1)]
        self.adapter.fetch_page("phone", None, 1)
        self.post.assert_called_once()
        self.assertEqual(self.transport.request_count, 2)
        self.assertGreaterEqual(self.transport.sleep.call_count, 1)
        self.assertEqual(len({c.kwargs["headers"]["Authorization"] for c in self.session.get.call_args_list}), 1)

    def test_invalid_or_incremental_requests_stop_before_auth(self):
        for query, cursor, limit, since in [("", None, 1, None), ("phone", "10000", 1, None),
                                           ("phone", None, 201, None), ("phone", None, 1, "2026-11-01")]:
            with self.assertRaises((ValueError, CollectionError)):
                self.adapter.fetch_page(query, cursor, limit, since)
        self.post.assert_not_called()
        self.session.get.assert_not_called()

    def test_missing_credentials_still_fail_before_auth(self):
        self.collector.client_secret = None
        with self.assertRaises(CollectionError) as error:
            self.adapter.fetch_page("phone", None, 1)
        self.assertEqual(error.exception.category, "credentials_missing")
        self.post.assert_not_called()
        self.session.get.assert_not_called()

    def test_runner_401_failure_resume_and_completed_checkpoint_behavior(self):
        self.session.get.side_effect = [self.response({}, 401), self.response({}, 401), self.page(1), self.page(2)]
        policy = SourcePolicy("ebay_browse", "official_api", True, "https://developer.ebay.com/join/api-license-agreement")
        with tempfile.TemporaryDirectory() as directory:
            state = FileState(Path(directory) / "state")
            sink = JsonlSink(Path(directory) / "outbox")
            runner = CollectionRunner(self.adapter, policy, state, sink)
            failed = runner.run("phone", "synthetic-job", max_items=2, page_size=1)
            self.assertEqual(failed["status"], "failed")
            self.assertIsNone(state.load_checkpoint("synthetic-job"))
            first = runner.run("phone", "synthetic-job", max_items=2, page_size=1)
            self.assertEqual(first["status"], "paused_at_page_budget")
            self.assertEqual(state.load_checkpoint("synthetic-job")["cursor"], "1")
            second = runner.run("phone", "synthetic-job", max_items=2, page_size=1)
            self.assertEqual(second["status"], "completed")
            self.assertEqual(second["stats"]["emitted"], 2)
            count = self.transport.request_count
            runner.run("phone", "synthetic-job", max_items=2, page_size=1)
            self.assertEqual(self.transport.request_count, count)
            self.assertEqual(len(list(sink.iter_unexpired(utc_now()))), 2)
