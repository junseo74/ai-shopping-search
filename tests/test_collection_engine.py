from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest
from unittest.mock import Mock

from backend.models import Product
from collection_engine.contracts import CollectionError, Offer, Page, SourcePolicy
from collection_engine.runner import CollectionRunner, public_url
from collection_engine.storage import FileState, JsonlSink, digest
from collection_engine.transport import HttpTransport


NOW = datetime(2026, 11, 8, tzinfo=timezone.utc)


def offer(number, price=10, url=None):
    return Offer(Product(product_name=f"Synthetic {number}", price=price, currency="USD",
        product_url=url or f"https://example.com/product/{number}", platform="test", data_source="synthetic"),
        str(number), str(number))


class FakeAdapter:
    source = "synthetic"

    def __init__(self, pages):
        self.pages, self.calls = pages, []

    def fetch_page(self, query, cursor, limit, since=None):
        self.calls.append(cursor)
        value = self.pages[cursor]
        if isinstance(value, Exception):
            raise value
        return value


class EngineTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.state = FileState(self.root / "state")
        self.sink = JsonlSink(self.root / "outbox")
        self.policy = SourcePolicy("synthetic", "synthetic", True, "local://tests",
            purposes=("validation",), validation_limit=100, synthetic=True)

    def tearDown(self):
        self.temporary.cleanup()

    def run_engine(self, adapter, job="job", **kwargs):
        return CollectionRunner(adapter, self.policy, self.state, self.sink, clock=lambda: NOW).run(
            "synthetic", job, **kwargs)

    def test_checkpoint_resume_and_no_request_after_completion(self):
        adapter = FakeAdapter({None: Page([offer(1)], "1"), "1": Page([offer(2)])})
        first = self.run_engine(adapter, max_items=2, page_size=1, max_pages=1)
        self.assertEqual(first["status"], "paused_at_page_budget")
        second = self.run_engine(adapter, max_items=2, page_size=1, max_pages=1)
        self.assertEqual(second["stats"]["emitted"], 2)
        self.assertEqual(second["status"], "completed")
        self.run_engine(adapter, max_items=2, page_size=1, max_pages=1)
        self.assertEqual(adapter.calls, [None, "1"])

    def test_duplicate_invalid_and_missing_field_metrics(self):
        adapter = FakeAdapter({None: Page([offer(1), offer(1), offer(2, price=None)])})
        result = self.run_engine(adapter, max_items=3, page_size=3)
        self.assertEqual(result["stats"]["duplicates"], 1)
        self.assertEqual(result["stats"]["invalid"], 1)
        self.assertEqual(result["stats"]["emitted"], 1)
        self.assertEqual(result["missing_field_rates"]["price"], 1 / 3)

    def test_incremental_unchanged_and_price_update(self):
        self.run_engine(FakeAdapter({None: Page([offer(1)])}), "initial", max_items=1)
        same = self.run_engine(FakeAdapter({None: Page([offer(1)])}), "same", max_items=1)
        changed = self.run_engine(FakeAdapter({None: Page([offer(1, 11)])}), "changed", max_items=1)
        self.assertEqual(same["stats"]["unchanged"], 1)
        self.assertEqual(same["stats"]["emitted"], 0)
        self.assertEqual(changed["stats"]["emitted"], 1)
        records = list(self.sink.iter_unexpired(NOW))
        self.assertEqual(len(records), 2)
        self.assertEqual(len({row["offer_key"] for row in records}), 1)
        self.assertEqual(len({row["event_id"] for row in records}), 2)

    def test_currency_is_part_of_offer_identity(self):
        first, second = offer(1), offer(1)
        second.product.currency = "EUR"
        result = self.run_engine(FakeAdapter({None: Page([first, second])}), max_items=2)
        self.assertEqual(result["stats"]["emitted"], 2)

    def test_sink_failure_does_not_advance_cursor_or_versions(self):
        adapter = FakeAdapter({None: Page([offer(1)])})
        real_sink = self.sink
        self.sink = Mock()
        self.sink.write_batch.side_effect = OSError("sensitive details must not be logged")
        failed = self.run_engine(adapter, max_items=1)
        self.assertEqual(failed["status"], "failed")
        self.assertIsNone(self.state.load_checkpoint("job"))
        self.assertNotIn("sensitive", json.dumps(failed))
        self.sink = real_sink
        self.assertEqual(self.run_engine(adapter, max_items=1)["stats"]["emitted"], 1)

    def test_crash_after_outbox_before_checkpoint_replays_idempotently(self):
        original = self.state.save_checkpoint
        self.state.save_checkpoint = Mock(side_effect=OSError("crash"))
        adapter = FakeAdapter({None: Page([offer(1)])})
        self.assertEqual(self.run_engine(adapter, max_items=1)["status"], "failed")
        self.state.save_checkpoint = original
        self.assertEqual(self.run_engine(adapter, max_items=1)["status"], "completed")
        self.assertEqual(len(list(self.sink.iter_unexpired(NOW))), 1)

    def test_crash_before_version_update_outbox_batch_reused(self):
        original = self.state.commit_versions
        self.state.commit_versions = Mock(side_effect=OSError("crash"))
        adapter = FakeAdapter({None: Page([offer(1)])})
        self.run_engine(adapter, max_items=1)
        self.state.commit_versions = original
        self.run_engine(adapter, max_items=1)
        self.assertEqual(len(list(self.sink.iter_unexpired(NOW))), 1)

    def test_failed_page_is_resumable(self):
        adapter = FakeAdapter({None: Page([offer(1)], "1"), "1": CollectionError("rate_limit", 429, 60)})
        failed = self.run_engine(adapter, max_items=2, page_size=1, max_pages=2)
        self.assertEqual(failed["errors"][0]["http_status"], 429)
        self.assertEqual(self.state.load_checkpoint("job")["cursor"], "1")
        adapter.pages["1"] = Page([offer(2)])
        self.assertTrue(self.run_engine(adapter, max_items=2, page_size=1)["done"])

    def test_policy_blocks_before_fetch_and_bulk_requires_permission(self):
        adapter = FakeAdapter({})
        runner = CollectionRunner(adapter, SourcePolicy("synthetic", "api"), self.state, self.sink)
        with self.assertRaises(CollectionError):
            runner.run("query", "job")
        with self.assertRaises(CollectionError):
            self.run_engine(adapter, max_items=101)
        self.assertEqual(adapter.calls, [])

    def test_job_parameters_cannot_change_on_resume(self):
        self.run_engine(FakeAdapter({None: Page([])}), max_items=1)
        with self.assertRaises(ValueError):
            self.run_engine(FakeAdapter({}), max_items=2)

    def test_pagination_loop_is_failure_not_success(self):
        adapter = FakeAdapter({None: Page([offer(1)], "1"), "1": Page([offer(2)], "1")})
        result = self.run_engine(adapter, max_items=3, page_size=1, max_pages=2)
        self.assertEqual(result["errors"][0]["category"], "pagination_loop")

    def test_expired_outbox_not_exported_and_version_can_refresh(self):
        self.run_engine(FakeAdapter({None: Page([offer(1)])}), max_items=1)
        later = NOW + timedelta(seconds=3601)
        self.assertEqual(list(self.sink.iter_unexpired(later)), [])
        runner = CollectionRunner(FakeAdapter({None: Page([offer(1)])}), self.policy, self.state, self.sink, lambda: later)
        result = runner.run("synthetic", "refresh", max_items=1)
        self.assertEqual(result["stats"]["emitted"], 1)

    def test_nonfinite_price_rejected(self):
        result = self.run_engine(FakeAdapter({None: Page([offer(1, float("inf"))])}), max_items=1)
        self.assertEqual(result["stats"]["invalid"], 1)

    def test_private_urls_rejected(self):
        for url in ("file:///tmp/x", "https://localhost/x", "https://127.0.0.1/x", "https://10.0.0.1/x", "https://user:pass@example.com/x"):
            self.assertFalse(public_url(url))
        self.assertTrue(public_url("https://example.com/product/1?variant=2"))

    def test_writer_lock_excludes_other_writer_and_can_be_reused(self):
        with self.state.lock():
            with self.assertRaises(OSError):
                with self.state.lock():
                    self.fail("Second writer acquired the same state directory")
        with self.state.lock():
            pass

    def test_process_exit_releases_lock_without_deleting_state(self):
        code = "import os,sys; from collection_engine.storage import FileState; s=FileState(sys.argv[1]); lease=s.lock(); lease.__enter__(); os._exit(0)"
        code = "import sys; sys.path.insert(0, " + repr(str(Path(__file__).resolve().parents[1])) + "); " + code
        result = subprocess.run([sys.executable, "-B", "-c", code, str(self.root / "state")], capture_output=True)
        self.assertEqual(result.returncode, 0)
        with self.state.lock():
            pass


class TransportTest(unittest.TestCase):
    def transport(self, responses):
        session = Mock()
        session.get.side_effect = responses
        return HttpTransport(session=session, sleep=Mock(), clock=lambda: 0, jitter=lambda: 0)

    def test_429_retry_after_respected_then_success(self):
        transport = self.transport([Mock(status_code=429, headers={"Retry-After": "5"}),
                                    Mock(status_code=200, json=lambda: {"ok": True})])
        self.assertTrue(transport.get_json("https://example.com/api")["ok"])
        self.assertIn(unittest.mock.call(5.0), transport.sleep.call_args_list)
        self.assertEqual(transport.request_count, 2)

    def test_long_retry_after_stops_instead_of_retrying_early(self):
        transport = self.transport([Mock(status_code=429, headers={"Retry-After": "120"})])
        with self.assertRaises(CollectionError) as raised:
            transport.get_json("https://example.com/api")
        self.assertEqual(raised.exception.retry_after, 120)
        self.assertEqual(transport.request_count, 1)

    def test_auth_and_redirect_do_not_retry_or_expose_url(self):
        for status in (401, 403, 302):
            transport = self.transport([Mock(status_code=status)])
            with self.assertRaises(CollectionError) as raised:
                transport.get_json("https://example.com/api?apiKey=secret")
            self.assertEqual(transport.request_count, 1)
            self.assertNotIn("secret", str(raised.exception))

    def test_503_retries_are_bounded(self):
        transport = self.transport([Mock(status_code=503, headers={})] * 3)
        with self.assertRaises(CollectionError):
            transport.get_json("https://example.com/api")
        self.assertEqual(transport.request_count, 3)

    def test_invalid_json_classified(self):
        response = Mock(status_code=200)
        response.json.side_effect = ValueError("sensitive response body")
        with self.assertRaisesRegex(CollectionError, "parsing_error"):
            self.transport([response]).get_json("https://example.com/api")
