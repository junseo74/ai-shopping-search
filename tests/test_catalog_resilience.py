"""Official API contracts exercised entirely with synthetic responses."""
import os
import json
from unittest.mock import Mock, patch

import pytest
import requests

from backend.collectors.apple_books import AppleBooksLookupCollector
from backend.collectors.ebay import EbayBrowseCollector
from backend.collectors.official_catalogs import YahooShoppingCollector, RakutenIchibaCollector, BestBuyProductsCollector
from backend.collectors.yes24 import Yes24ProductCollector
from collection_engine.adapters import BackendCollectorAdapter, EbayPagedAdapter, PagedCollectorAdapter
from collection_engine.contracts import CollectionError, SourcePolicy
from collection_engine.registry import build_adapter
from collection_engine.runner import CollectionRunner
from collection_engine.storage import FileState, JsonlSink
from collection_engine.transport import HttpTransport


FACTORIES = [YahooShoppingCollector, RakutenIchibaCollector, BestBuyProductsCollector]
ROW_KEYS = ["hits", "Items", "products"]


def catalog(factory, body):
    body = dict(body)
    key, total = {YahooShoppingCollector: ("hits", "totalResultsAvailable"),
                  RakutenIchibaCollector: ("Items", "pageCount"),
                  BestBuyProductsCollector: ("products", "totalPages")}[factory]
    if isinstance(body.get(key), list) and body[key] and total not in body:
        body[total] = len(body[key])
    http = Mock()
    http.get_json.return_value = body
    with patch.dict(os.environ, {key: "fixture-credential" for key in factory.required_keys}):
        return factory(http), http


def raw_row(factory, number=1):
    if factory is YahooShoppingCollector:
        return {"code": f"shop:{number}", "name": f"Synthetic {number}", "price": "1,200", "url": f"https://example.com/{number}"}
    if factory is RakutenIchibaCollector:
        return {"itemCode": f"shop:{number}", "itemName": f"Synthetic {number}", "itemPrice": "1,200", "itemUrl": f"https://example.com/{number}"}
    return {"sku": number, "name": f"Synthetic {number}", "salePrice": "19.99", "url": f"https://example.com/{number}"}


@pytest.mark.parametrize("factory,key", list(zip(FACTORIES, ROW_KEYS)))
@pytest.mark.parametrize("rows", [None, {}, "bad", [None], ["bad"]])
def test_bad_row_shapes_are_sanitized_parsing_errors(factory, key, rows):
    collector, _ = catalog(factory, {key: rows})
    with pytest.raises(CollectionError, match="parsing_error"):
        collector.fetch_page("q", None, 1)


@pytest.mark.parametrize("factory,key", list(zip(FACTORIES, ROW_KEYS)))
def test_empty_catalogs_end_pagination(factory, key):
    collector, _ = catalog(factory, {key: []})
    page = collector.fetch_page("q", None, 1)
    assert page.offers == []
    assert page.next_cursor is None


@pytest.mark.parametrize("factory,key", list(zip(FACTORIES, ROW_KEYS)))
def test_too_many_provider_rows_are_rejected(factory, key):
    collector, _ = catalog(factory, {key: [raw_row(factory), raw_row(factory, 2)]})
    with pytest.raises(CollectionError, match="page_limit_violation"):
        collector.fetch_page("q", None, 1)


@pytest.mark.parametrize("factory,key", list(zip(FACTORIES, ROW_KEYS)))
def test_explicit_price_strings_map_without_seller_fabrication(factory, key):
    collector, _ = catalog(factory, {key: [raw_row(factory)]})
    item = collector.fetch_page("q", None, 1).offers[0]
    assert item.product.price == (19.99 if factory is BestBuyProductsCollector else 1200)
    assert item.product.seller is None


@pytest.mark.parametrize("factory", FACTORIES)
@pytest.mark.parametrize("cursor", ["invalid", "-1", "0", "1:0", "1:999999", "2:2:2"])
def test_bad_cursor_never_makes_request(factory, cursor):
    collector, http = catalog(factory, {})
    with pytest.raises(CollectionError):
        collector.fetch_page("q", cursor, 1)
    http.get_json.assert_not_called()


@pytest.mark.parametrize("factory,key,metadata,size_param", [
    (RakutenIchibaCollector, "Items", "pageCount", "hits"),
    (BestBuyProductsCollector, "products", "totalPages", "pageSize")])
def test_final_page_size_change_never_repeats_or_skips_items(factory, key, metadata, size_param, tmp_path):
    collector, http = catalog(factory, {})
    requested = []
    def response(url, **kwargs):
        params = kwargs["params"]
        page, size = params["page"], params[size_param]
        requested.append((page, size))
        start = (page - 1) * size
        all_rows = [raw_row(factory, number) for number in range(1, 4)]
        return {key: all_rows[start:start + size], metadata: (3 + size - 1) // size}
    http.get_json.side_effect = response
    runner = CollectionRunner(PagedCollectorAdapter(collector),
        SourcePolicy(collector.metadata.source_name, "official_api", True, "local://tests"),
        FileState(tmp_path / "state"), JsonlSink(tmp_path / "outbox"))
    first = runner.run("q", "job", max_items=3, page_size=2)
    assert first["status"] == "paused_at_page_budget"
    result = runner.run("q", "job", max_items=3, page_size=2)
    assert result["status"] == "completed"
    assert result["stats"]["emitted"] == 3
    assert requested == [(1, 2), (3, 1)]


def ebay_row(number=1):
    return {"itemId": str(number), "title": f"Synthetic {number}",
        "price": {"value": "10", "currency": "USD"}, "itemWebUrl": f"https://www.ebay.com/itm/{number}"}


def ebay(body):
    with patch.dict(os.environ, {"EBAY_CLIENT_ID": "fixture-id", "EBAY_CLIENT_SECRET": "fixture-secret"}):
        original = EbayBrowseCollector()
    original._get_access_token = Mock(return_value="fixture-token")
    http = Mock()
    http.get_json.return_value = body
    return EbayPagedAdapter(original, http), http


@pytest.mark.parametrize("body", [{}, {"errors": [{"message": "private"}]}, {"total": "bad", "itemSummaries": []},
    {"total": 1, "itemSummaries": [None]}, {"total": 1, "itemSummaries": [{"itemId": "1"}]}])
def test_ebay_error_or_malformed_response_never_counts_as_empty_success(body):
    adapter, _ = ebay(body)
    with pytest.raises(CollectionError) as error:
        adapter.fetch_page("q", None, 1)
    assert "private" not in str(error.value)


def test_ebay_zero_results_is_valid_empty_page():
    adapter, _ = ebay({"total": 0})
    assert adapter.fetch_page("q", None, 1).offers == []


def test_ebay_token_expiry_refreshes_before_next_search():
    adapter, _ = ebay({"total": 3, "itemSummaries": [ebay_row()]})
    adapter.fetch_page("q", None, 1)
    adapter.collector.token_expires_at = 0
    adapter.fetch_page("q", "1", 1)
    assert adapter.collector._get_access_token.call_count == 2


def test_ebay_401_stops_after_one_retry_then_explicit_resume_refreshes():
    adapter, http = ebay({"total": 0})
    http.get_json.side_effect = [CollectionError("authentication_failed", 401),
                                CollectionError("authentication_failed", 401), {"total": 0}]
    with pytest.raises(CollectionError, match="authentication_failed"):
        adapter.fetch_page("q", None, 1)
    assert http.get_json.call_count == 2
    assert adapter.collector._access_token is None
    adapter.fetch_page("q", None, 1)
    assert adapter.collector._get_access_token.call_count == 3


def test_ebay_offset_alignment_respects_remaining_budget():
    adapter, http = ebay({"total": 5, "itemSummaries": [ebay_row(4)]})
    adapter.fetch_page("q", "3", 2)
    assert http.get_json.call_args.kwargs["params"]["limit"] == 1
    assert http.get_json.call_args.kwargs["params"]["offset"] == 3


def test_ebay_missing_seller_stays_missing_and_foreign_shipping_not_assumed():
    item = ebay_row()
    item["shippingOptions"] = [{"shippingCost": {"value": "100", "currency": "JPY"}}]
    adapter, _ = ebay({"total": 1, "itemSummaries": [item]})
    mapped = adapter.fetch_page("q", None, 1).offers[0].product
    assert mapped.seller is None
    assert mapped.shipping_fee is None


@pytest.mark.parametrize("currency", [None, "", "US1"])
def test_ebay_never_defaults_missing_currency(currency):
    item = ebay_row()
    item["price"]["currency"] = currency
    adapter, _ = ebay({"total": 1, "itemSummaries": [item]})
    with pytest.raises(CollectionError, match="invalid_currency"):
        adapter.fetch_page("q", None, 1)


def test_oauth_uses_common_transport_without_redirects_and_closes_response():
    response = Mock(status_code=200, json=lambda: {"access_token": "fixture-token", "expires_in": 7200})
    session = Mock()
    session.post.return_value = response
    http = HttpTransport(session=session, sleep=Mock())
    with patch.dict(os.environ, {"EBAY_CLIENT_ID": "fixture-id", "EBAY_CLIENT_SECRET": "fixture-secret"}):
        collector = EbayBrowseCollector(token_transport=http)
    assert collector._get_access_token() == "fixture-token"
    assert collector.token_expires_at is not None
    assert session.post.call_args.kwargs["allow_redirects"] is False
    assert session.post.call_args.kwargs["timeout"] == 20
    response.close.assert_called_once()


@pytest.mark.parametrize("body", [[], {"access_token": []}, {"access_token": "t", "expires_in": "NaN"}, {"access_token": "t", "expires_in": 0}])
def test_oauth_malformed_token_or_expiry_rejected(body):
    http = Mock()
    http.post_json.return_value = body
    with patch.dict(os.environ, {"EBAY_CLIENT_ID": "fixture", "EBAY_CLIENT_SECRET": "fixture"}):
        collector = EbayBrowseCollector(token_transport=http)
    with pytest.raises(RuntimeError):
        collector._get_access_token()


def test_apple_transport_preserves_robots_gate_and_native_identity():
    http = Mock()
    http.get_text.return_value = "User-agent: *\nAllow: /lookup"
    http.get_json.return_value = {"results": [{"kind": "ebook", "trackId": 123, "trackName": "Synthetic book",
        "price": "19.99", "currency": "USD", "trackViewUrl": "https://books.apple.com/us/book/id123"}]}
    page = BackendCollectorAdapter(AppleBooksLookupCollector(transport=http)).fetch_page("9780316069359", None, 1)
    assert page.offers[0].product_id == "123"
    assert page.offers[0].identity_basis == "provider_id"
    assert page.offers[0].product.price == 19.99
    http.get_text.assert_called_once()
    http.get_json.assert_called_once()
    http.get_text.return_value = "User-agent: *\nDisallow: /lookup"
    http.get_json.reset_mock()
    with pytest.raises(CollectionError, match="robots_disallowed"):
        AppleBooksLookupCollector(transport=http).collect("9780316069359", 1)
    http.get_json.assert_not_called()


def test_yes24_transport_and_native_identity():
    http = Mock()
    http.get_json.return_value = {"success": True, "data": {"items": [{"itemId": 456,
        "title": "Synthetic book", "salePrice": "10,000", "link": "https://www.yes24.com/product/goods/456"}]}}
    with patch.dict(os.environ, {"YES24_API_KEY": "fixture-secret"}):
        collector = Yes24ProductCollector(transport=http)
    item = BackendCollectorAdapter(collector).fetch_page("book", None, 1).offers[0]
    assert item.product_id == "456"
    assert item.identity_basis == "provider_id"
    assert item.product.price == 10000


@pytest.mark.parametrize("source", ["apple_books_lookup", "yes24_api", "ebay_browse"])
def test_registry_injects_common_transport(source):
    with patch("requests.sessions.Session.request", side_effect=AssertionError("network")):
        adapter = build_adapter(source)
    active = adapter.transport if source == "ebay_browse" else adapter.collector.transport
    assert isinstance(active, HttpTransport)


def test_unverified_elevenst_secure_route_blocked_before_http():
    with patch("requests.get", side_effect=AssertionError("network")):
        with pytest.raises(CollectionError, match="secure_endpoint_unverified"):
            build_adapter("elevenst")


@pytest.mark.parametrize("factory,body", [
    (AppleBooksLookupCollector, {"results": None}),
    (AppleBooksLookupCollector, {"results": [None]}),
    (Yes24ProductCollector, {"success": True, "data": []}),
    (Yes24ProductCollector, {"success": True, "data": {"items": None}})])
def test_single_shot_api_bad_shapes_are_classified(factory, body):
    http = Mock()
    http.get_text.return_value = "User-agent: *\nAllow: /lookup"
    http.get_json.return_value = body
    with patch.dict(os.environ, {"YES24_API_KEY": "fixture"}):
        collector = factory(transport=http)
    with pytest.raises(CollectionError, match="parsing_error"):
        collector.collect("9780316069359" if factory is AppleBooksLookupCollector else "book", 1)


def test_old_verification_script_defaults_to_offline_diagnostics(capsys):
    from samples.verify_common_engine import main as verify
    with patch("requests.sessions.Session.request", side_effect=AssertionError("network")), patch("samples.verify_common_engine.build_adapter", side_effect=AssertionError("adapter")):
        assert verify([]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["network_used"] is False


@pytest.mark.parametrize("error,category", [(ValueError("private"), "parsing_error"),
    (TypeError("private"), "parsing_error"), (requests.Timeout("private"), "timeout")])
def test_backend_adapter_sanitizes_typed_collector_failures(error, category):
    collector = Mock()
    collector.metadata.source_name = "synthetic"
    collector.collect.side_effect = error
    with pytest.raises(CollectionError, match=category) as raised:
        BackendCollectorAdapter(collector).fetch_page("q", None, 1)
    assert "private" not in str(raised.value)


def test_yes24_api_error_is_classified_without_echoing_payload():
    http = Mock()
    http.get_json.return_value = {"success": False, "errorCode": "fixture-secret", "message": "private"}
    with patch.dict(os.environ, {"YES24_API_KEY": "fixture-secret"}):
        collector = Yes24ProductCollector(transport=http)
    with pytest.raises(CollectionError, match="api_error") as raised:
        collector.collect("book", 1)
    assert "private" not in str(raised.value)
    assert "fixture-secret" not in str(raised.value)


@pytest.mark.parametrize("value", [True, "bad", "-1", "NaN"])
def test_ebay_shipping_amount_is_validated_before_float_coercion(value):
    item = ebay_row()
    item["shippingOptions"] = [{"shippingCost": {"value": value, "currency": "USD"}}]
    adapter, _ = ebay({"total": 1, "itemSummaries": [item]})
    with pytest.raises(CollectionError, match="invalid_price"):
        adapter.fetch_page("q", None, 1)


@pytest.mark.parametrize("label,expected", [("Like New", "used"), ("New with tags", "new"), ("Seller refurbished", "refurbished"), ("Renewed", "unknown")])
def test_ebay_condition_does_not_classify_like_new_as_new(label, expected):
    assert EbayBrowseCollector()._map_condition(label) == expected


@pytest.mark.parametrize("factory,key,metadata", [
    (YahooShoppingCollector, "hits", "totalResultsAvailable"),
    (RakutenIchibaCollector, "Items", "pageCount"),
    (BestBuyProductsCollector, "products", "totalPages")])
def test_nonempty_response_missing_pagination_metadata_is_not_false_completion(factory, key, metadata):
    collector, http = catalog(factory, {})
    http.get_json.return_value = {key: [raw_row(factory)]}
    with pytest.raises(CollectionError, match="parsing_error"):
        collector.fetch_page("q", None, 1)


@pytest.mark.parametrize("metadata", [None, "private-value", -1, 1.5, True])
def test_invalid_count_metadata_is_sanitized(metadata):
    collector, _ = catalog(YahooShoppingCollector, {"hits": [raw_row(YahooShoppingCollector)], "totalResultsAvailable": metadata})
    with pytest.raises(CollectionError, match="parsing_error") as raised:
        collector.fetch_page("q", None, 1)
    assert "private-value" not in str(raised.value)
