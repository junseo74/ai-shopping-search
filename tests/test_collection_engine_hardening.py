"""Offline regressions for the engine audit; no provider credentials required."""
from datetime import datetime, timedelta, timezone
import json
import socket
from unittest.mock import Mock, patch

import pytest
import requests

from backend.models import Product
from collection_engine.__main__ import main
from collection_engine.contracts import CollectionError, Offer, Page, SourcePolicy
from collection_engine.diagnostics import diagnose
from collection_engine.quality import price_number, currency_code
from collection_engine.registry import credential_presence, policies
from collection_engine.responses import page_request
from collection_engine.runner import CollectionRunner
from collection_engine.storage import FileState, JsonlSink
from collection_engine.transport import HttpTransport


NOW = datetime(2026, 11, 11, tzinfo=timezone.utc)


def product(number=1, **updates):
    values = dict(product_name=f"Synthetic {number}", price=10, currency="USD",
        platform="test", data_source="synthetic", product_url=f"https://example.com/{number}")
    values.update(updates)
    return Product(**values)


def offer(number=1, **updates):
    return Offer(product(number, **updates), str(number), str(number))


class Adapter:
    source = "synthetic"

    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def fetch_page(self, query, cursor, limit, since=None):
        self.calls.append((cursor, limit))
        return self.pages[cursor]


def engine(tmp_path, adapter):
    return CollectionRunner(adapter,
        SourcePolicy("synthetic", "local_synthetic", True, "local://tests", validation_limit=100, synthetic=True),
        FileState(tmp_path / "state"), JsonlSink(tmp_path / "outbox"), clock=lambda: NOW)


def transport(responses, **kwargs):
    session = Mock()
    session.get.side_effect = responses
    return HttpTransport(session=session, sleep=Mock(), clock=lambda: 0, jitter=lambda: 0, **kwargs)


@pytest.mark.parametrize("value,expected", [("1,234.50", 1234.5), (" 0 ", 0), ("19.99", 19.99), (10, 10)])
def test_explicit_price_normalization(value, expected):
    assert price_number(value) == expected


@pytest.mark.parametrize("value", ["1,2", "1.234,50", "$10", "100원", "문의", "NaN", "Infinity", "-1", True, float("inf"), []])
def test_ambiguous_or_invalid_prices_rejected(value):
    with pytest.raises(CollectionError, match="invalid_price"):
        price_number(value)


@pytest.mark.parametrize("value", ["US1", "ＵＳＤ", "원", "", None])
def test_invalid_currency_rejected(value):
    with pytest.raises(CollectionError, match="invalid_currency"):
        currency_code(value)


def test_currency_normalization_preserves_amount_without_fx(tmp_path):
    item = offer(price=19.99, currency="usd")
    result = engine(tmp_path, Adapter({None: Page([item])})).run("q", "job", max_items=1)
    assert result["stats"]["emitted"] == 1
    records = list(JsonlSink(tmp_path / "outbox").iter_unexpired(NOW))
    assert records[0]["product"]["currency"] == "USD"
    assert records[0]["product"]["price"] == 19.99
    assert item.product.currency == "usd"  # The adapter's object was not mutated.
    assert records[0]["source_product_id"] == "1"
    assert records[0]["product"]["seller"] is None


def test_unvalidated_string_price_is_normalized_at_boundary(tmp_path):
    item = offer()
    item.product.price = "1,234.50"
    result = engine(tmp_path, Adapter({None: Page([item])})).run("q", "job", max_items=1)
    assert result["stats"]["emitted"] == 1
    record = next(JsonlSink(tmp_path / "outbox").iter_unexpired(NOW))
    assert record["product"]["price"] == 1234.5


@pytest.mark.parametrize("field,value", [("price", "bad"), ("shipping_fee", float("inf")), ("platform", "bad")])
def test_invalid_mutated_product_is_rejected_without_failing_page(tmp_path, field, value):
    invalid = offer(2)
    setattr(invalid.product, field, value)
    result = engine(tmp_path, Adapter({None: Page([offer(), invalid])})).run("q", "job", max_items=2)
    assert result["status"] == "completed"
    assert result["stats"]["invalid"] == 1
    assert result["stats"]["emitted"] == 1


def test_missing_url_not_invented(tmp_path):
    result = engine(tmp_path, Adapter({None: Page([offer(product_url=None)])})).run("q", "job", max_items=1)
    assert result["stats"]["reasons"] == {"invalid_product_url": 1}
    assert list((tmp_path / "outbox").glob("*.jsonl")) == []


def test_cursor_cycle_detected_across_resume(tmp_path):
    adapter = Adapter({None: Page([offer(1)], "a"), "a": Page([offer(2)], "b"), "b": Page([offer(3)], "a")})
    runner = engine(tmp_path, adapter)
    assert runner.run("q", "job", max_items=5, page_size=1)["status"] == "paused_at_page_budget"
    assert runner.run("q", "job", max_items=5, page_size=1)["status"] == "paused_at_page_budget"
    result = runner.run("q", "job", max_items=5, page_size=1)
    assert result["errors"][0]["category"] == "pagination_loop"
    assert runner.state.load_checkpoint("job")["cursor"] == "b"
    assert result["stats"]["pages"] == 2


def test_empty_page_without_cursor_completes(tmp_path):
    result = engine(tmp_path, Adapter({None: Page([])})).run("q", "job")
    assert result["status"] == "completed"
    assert result["stats"]["emitted"] == 0


def test_empty_page_with_cursor_stops_and_remains_resumable(tmp_path):
    runner = engine(tmp_path, Adapter({None: Page([], "next")}))
    result = runner.run("q", "job", max_pages=10)
    assert result["errors"][0]["category"] == "empty_page_with_cursor"
    assert runner.state.load_checkpoint("job") is None
    assert len(runner.adapter.calls) == 1


@pytest.mark.parametrize("page", [Page([], rejected=-1), Page([], next_cursor=12), Page([offer(), offer(2)])])
def test_invalid_page_never_advances_checkpoint(tmp_path, page):
    runner = engine(tmp_path, Adapter({None: page}))
    result = runner.run("q", "job", max_items=1)
    assert result["status"] == "failed"
    assert runner.state.load_checkpoint("job") is None


def test_page_and_item_budgets_are_hard_bounds(tmp_path):
    adapter = Adapter({None: Page([offer(1)], "a"), "a": Page([offer(2)], "b")})
    runner = engine(tmp_path, adapter)
    assert runner.run("q", "job", max_items=2, page_size=1)["stats"]["received"] == 1
    result = runner.run("q", "job", max_items=2, page_size=1, max_pages=10)
    assert result["status"] == "completed"
    assert result["stats"]["received"] == 2
    assert len(adapter.calls) == 2


@pytest.mark.parametrize("value", ["nan", "inf", "-inf", "garbage", "", None])
def test_retry_after_invalid_values_do_not_produce_nonfinite_waits(value):
    assert HttpTransport.retry_seconds(value) is None


def test_retry_after_http_date():
    from email.utils import format_datetime
    future = format_datetime(datetime.now(timezone.utc) + timedelta(seconds=60))
    assert 58 <= HttpTransport.retry_seconds(future) <= 60


def test_timeout_retries_are_bounded_and_sanitized():
    http = transport([requests.Timeout("secret-url")] * 3)
    with pytest.raises(CollectionError, match="timeout") as error:
        http.get_json("https://example.com/?key=secret")
    assert http.request_count == 3
    assert "secret" not in str(error.value)
    assert [call.args[0] for call in http.sleep.call_args_list if call.args[0] in (1, 2)] == [1, 2]


def test_connection_failure_can_recover():
    http = transport([requests.ConnectionError("secret"), Mock(status_code=200, json=lambda: {})])
    assert http.get_json("https://example.com") == {}
    assert http.request_count == 2


@pytest.mark.parametrize("status,category", [(401, "authentication_failed"), (403, "permission_denied"), (404, "access_error"), (302, "access_error")])
def test_no_retry_for_permanent_errors_and_response_closed(status, category):
    response = Mock(status_code=status)
    http = transport([response])
    with pytest.raises(CollectionError, match=category):
        http.get_json("https://example.com")
    assert http.request_count == 1
    response.close.assert_called_once()


def test_retry_limit_has_serializable_error():
    http = transport([Mock(status_code=429, headers={"Retry-After": "inf"})] * 3)
    with pytest.raises(CollectionError) as raised:
        http.get_json("https://example.com")
    assert raised.value.category == "rate_limit"
    assert raised.value.retry_after == 4
    json.dumps({"retry_after": raised.value.retry_after}, allow_nan=False)


@pytest.mark.parametrize("body", [[], None, "text", 1])
def test_wrong_top_level_json_type_rejected(body):
    http = transport([Mock(status_code=200, json=lambda: body)])
    with pytest.raises(CollectionError, match="parsing_error"):
        http.get_json("https://example.com")


@pytest.mark.parametrize("kwargs", [{"max_attempts": 0}, {"max_attempts": True}, {"interval": -1}, {"max_wait": float("inf")}, {"timeout": None}, {"timeout": 0}, {"timeout": (1, 0)}])
def test_transport_configuration_cannot_disable_bounds(kwargs):
    with pytest.raises(ValueError):
        HttpTransport(**kwargs)


def test_timeout_pair_and_redirect_guard():
    http = transport([Mock(status_code=200, json=lambda: {})], timeout=(5, 15))
    http.get_json("https://example.com")
    assert http.session.get.call_args.kwargs["timeout"] == (5, 15)
    assert http.session.get.call_args.kwargs["allow_redirects"] is False
    with pytest.raises(ValueError):
        http.get_json("https://example.com", timeout=None)


def test_diagnostics_no_network_no_collector_construction_or_secrets(capsys):
    values = {key: "fixture-private" for policy in policies().values() for key in policy.credential_env}
    with patch("requests.sessions.Session.request", side_effect=AssertionError("network")), patch("collection_engine.__main__.build_adapter", side_effect=AssertionError("adapter")):
        result = diagnose(environ=values)
        assert main([]) == 0
    assert result["network_used"] is False
    assert len(result["sources"]) == len(policies())
    assert "fixture-private" not in json.dumps(result)
    assert "fixture-private" not in capsys.readouterr().out
    yahoo = next(row for row in result["sources"] if row["source"] == "yahoo_shopping")
    assert yahoo["live_supported"] is True
    assert yahoo["ready_for_explicit_live_check"] is False
    assert yahoo["blockers"] == ["policy_restriction"]


def test_credentials_whitespace_is_missing_and_names_only():
    policy = SourcePolicy("x", "api", credential_env=("KEY_A", "KEY_B"))
    assert credential_presence(policy, {"KEY_A": " ", "KEY_B": "fixture-secret"}) == {"KEY_A": False, "KEY_B": True}


def test_diagnostic_source_filter_and_unknown_source():
    result = diagnose("elevenst", environ={})
    assert len(result["sources"]) == 1
    assert result["sources"][0]["live_supported"] is False
    with pytest.raises(ValueError):
        diagnose("not-a-source", environ={})


def test_live_flag_required_before_any_output_or_fetch(tmp_path):
    with patch("collection_engine.__main__.build_adapter", side_effect=AssertionError("adapter")):
        with pytest.raises(SystemExit) as raised:
            main(["--source", "ebay_browse", "--query", "q", "--job-id", "id", "--output", str(tmp_path)])
    assert raised.value.code == 2
    assert list(tmp_path.iterdir()) == []


def test_corrupt_saved_outbox_stops_before_checkpoint(tmp_path):
    runner = engine(tmp_path, Adapter({None: Page([offer()])}))
    original = runner.state.commit_versions
    runner.state.commit_versions = Mock(side_effect=OSError("crash"))
    assert runner.run("q", "job", max_items=1)["status"] == "failed"
    saved = next((tmp_path / "outbox").glob("*.jsonl"))
    saved.write_text("not-json", encoding="utf-8")
    runner.state.commit_versions = original
    result = runner.run("q", "job", max_items=1)
    assert result["status"] == "failed"
    assert runner.state.load_checkpoint("job") is None
    assert saved.read_text(encoding="utf-8") == "not-json"


@pytest.mark.parametrize("cursor,limit,expected", [(None, 2, (1, 2)), ("2:2", 1, (3, 1)), ("2:3", 2, (4, 1)), ("2", 1, (2, 1))])
def test_page_size_transition_preserves_logical_position(cursor, limit, expected):
    assert page_request(cursor, limit) == expected


def test_checkpoint_failure_reports_durable_progress_only(tmp_path):
    runner = engine(tmp_path, Adapter({None: Page([offer()])}))
    runner.state.save_checkpoint = Mock(side_effect=OSError("private"))
    result = runner.run("q", "job", max_items=1)
    assert result["status"] == "failed"
    assert result["done"] is False
    assert result["stats"]["pages"] == 0
    assert result["stats"]["received"] == 0
    assert "private" not in json.dumps(result)


def test_policy_change_requires_new_job(tmp_path):
    from dataclasses import replace
    runner = engine(tmp_path, Adapter({None: Page([offer()], "a")}))
    runner.run("q", "job", max_items=2, page_size=1)
    runner.policy = replace(runner.policy, omitted_fields=("image_url",))
    with pytest.raises(ValueError, match="policy or adapter context changed"):
        runner.run("q", "job", max_items=2, page_size=1)
    assert len(runner.adapter.calls) == 1


def test_adapter_context_change_requires_new_job(tmp_path):
    runner = engine(tmp_path, Adapter({None: Page([offer()], "a")}))
    runner.adapter.checkpoint_context = {"marketplace_id": "A"}
    runner.run("q", "job", max_items=2, page_size=1)
    runner.adapter.checkpoint_context = {"marketplace_id": "B"}
    with pytest.raises(ValueError, match="adapter context changed"):
        runner.run("q", "job", max_items=2, page_size=1)
    assert len(runner.adapter.calls) == 1


def test_tampered_saved_product_is_rejected_even_when_event_id_matches(tmp_path):
    runner = engine(tmp_path, Adapter({None: Page([offer()])}))
    runner.state.commit_versions = Mock(side_effect=OSError("crash"))
    runner.run("q", "job", max_items=1)
    saved = next((tmp_path / "outbox").glob("*.jsonl"))
    row = json.loads(saved.read_text(encoding="utf-8"))
    row["product"]["price"] = 999
    saved.write_text(json.dumps(row) + "\n", encoding="utf-8")
    result = runner.run("q", "job", max_items=1)
    assert result["errors"][0]["category"] == "outbox_corrupt"
    assert runner.state.load_checkpoint("job") is None
    with pytest.raises(CollectionError, match="outbox_corrupt"):
        list(runner.sink.iter_unexpired(NOW))


def test_corrupt_checkpoint_fails_before_fetch_and_is_preserved(tmp_path):
    from collection_engine.storage import digest
    runner = engine(tmp_path, Adapter({None: Page([offer()], "a")}))
    runner.run("q", "job", max_items=2, page_size=1)
    path = tmp_path / "state" / "jobs" / (digest("job") + ".json")
    path.write_text('{"signature": "bad"}', encoding="utf-8")
    with pytest.raises(CollectionError, match="checkpoint_corrupt"):
        runner.run("q", "job", max_items=2, page_size=1)
    assert len(runner.adapter.calls) == 1
    assert path.read_text(encoding="utf-8") == '{"signature": "bad"}'


def test_atomic_json_failure_keeps_existing_file_and_cleans_temporary(tmp_path):
    from collection_engine.storage import atomic_json
    path = tmp_path / "saved.json"
    atomic_json(path, {"ok": True})
    with pytest.raises(ValueError):
        atomic_json(path, {"bad": float("nan")})
    assert json.loads(path.read_text(encoding="utf-8")) == {"ok": True}
    assert list(tmp_path.glob(".pending-*")) == []


def test_adapter_rejections_have_reason_counts_without_double_counting(tmp_path):
    result = engine(tmp_path, Adapter({None: Page([offer()], rejected=1)})).run("q", "job", max_items=2)
    assert result["stats"]["received"] == 2
    assert result["stats"]["invalid"] == 1
    assert result["stats"]["reasons"] == {"adapter_rejected": 1}


def test_default_suite_blocks_external_resolution_before_dns():
    with pytest.raises(RuntimeError, match="External network is disabled"):
        socket.getaddrinfo("external.invalid", 443)


def test_default_suite_blocks_direct_external_socket_before_connect():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
        with pytest.raises(RuntimeError, match="External network is disabled"):
            connection.connect(("203.0.113.1", 443))


@pytest.mark.parametrize("url", ["https://localhost./item", "https://shop.localhost/item", "https://127.0.0.1./item", "https://example.com:bad/item"])
def test_product_url_validation_rejects_local_aliases_and_invalid_ports(url):
    from collection_engine.runner import public_url
    assert public_url(url) is False
