import json
import unittest
from unittest.mock import patch

from crawler_engine.extractors.joongna import extract_joongna_candidates
from crawler_engine.models import CrawlRequest
from crawler_engine.sites.joongna import JoongnaSource
from crawler_engine.sources import available_sources, select_sources


def _item(
    seq=123,
    title="Galaxy S25 256GB",
    price=700000,
    image_url="https://img2.joongna.com/media/original/item.jpg?impolicy=thumb&size=150",
    state=0,
    extra=None,
):
    item = {
        "seq": seq,
        "title": title,
        "price": price,
        "url": image_url,
        "state": state,
        "sortDate": "2026-10-13 10:41:06",
        "mainLocationName": "Innovation-dong",
        "locationNames": ["Jeonju Innovation-dong"],
        "storeSeq": 10530536,
        "userType": 0,
        "certifySellerFlag": False,
        "wishCount": 2,
        "chatCount": 3,
    }
    if extra:
        item.update(extra)
    return item


def _payload(items, code=0, total_size=100):
    return {
        "meta": {"code": code, "message": "SUCCESS" if code == 0 else "ERROR"},
        "data": {
            "totalSize": total_size,
            "items": items,
        },
    }


def _page_payload(*pages):
    return json.dumps({"pages": list(pages)}, ensure_ascii=False)


def _page(page, items, status=200, code=0):
    return {
        "page": page,
        "http_status": status,
        "payload": _payload(items, code=code),
        "item_count": len(items),
    }


class JoongnaSourceTest(unittest.TestCase):
    def test_source_url_and_metadata(self):
        source = available_sources()["joongna"]
        url = source.build_search_url(CrawlRequest(query="Galaxy S25", include_used=True))

        self.assertEqual(url, "https://web.joongna.com/search/Galaxy%20S25")
        self.assertEqual(source.metadata.source, "joongna")
        self.assertEqual(source.metadata.display_name, "Joonggonara")
        self.assertEqual(source.metadata.default_condition, "used")
        self.assertTrue(source.metadata.used_only)

    def test_used_source_requires_include_used(self):
        self.assertEqual(select_sources(CrawlRequest(query="Galaxy S25", include_used=False), "joongna"), [])
        self.assertEqual(len(select_sources(CrawlRequest(query="Galaxy S25", include_used=True), "joongna")), 1)

    def test_search_body_uses_expected_pagination_fields(self):
        body = JoongnaSource()._search_body("Galaxy S25", page=1, first_quantity=20, quantity=10)

        self.assertEqual(body["searchWord"], "Galaxy S25")
        self.assertEqual(body["page"], 1)
        self.assertEqual(body["firstQuantity"], 20)
        self.assertEqual(body["quantity"], 10)
        self.assertEqual(body["saleYn"], "SALE_N")

    def test_fetch_search_results_requests_only_needed_pages_for_limit(self):
        source = JoongnaSource()
        calls = []

        def fake_post(url, body, timeout_ms):
            calls.append(body)
            items = [_item(seq=body["page"] * 10 + index) for index in range(body["quantity"])]
            return 200, _payload(items)

        with patch.object(source, "_post_json", side_effect=fake_post):
            result = json.loads(source.fetch_search_results(CrawlRequest(query="Galaxy S25", include_used=True, limit=20)))

        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["page"], 0)
        self.assertEqual(calls[0]["firstQuantity"], 20)
        self.assertEqual(result["pages"][0]["item_count"], 20)

    def test_fetch_search_results_handles_page_zero_and_page_one(self):
        source = JoongnaSource()
        calls = []

        def fake_post(url, body, timeout_ms):
            calls.append(body)
            count = body["firstQuantity"] if body["page"] == 0 else body["quantity"]
            return 200, _payload([_item(seq=body["page"] * 100 + index) for index in range(count)])

        with patch.object(source, "_post_json", side_effect=fake_post):
            result = json.loads(source.fetch_search_results(CrawlRequest(query="Galaxy S25", include_used=True, limit=30)))

        self.assertEqual([call["page"] for call in calls], [0, 1])
        self.assertEqual(result["pages"][0]["item_count"], 24)
        self.assertEqual(result["pages"][1]["item_count"], 6)

    def test_fetch_search_results_stops_on_api_error(self):
        source = JoongnaSource()

        with patch.object(source, "_post_json", return_value=(500, None)):
            result = json.loads(source.fetch_search_results(CrawlRequest(query="Galaxy S25", include_used=True, limit=20)))

        self.assertEqual(len(result["pages"]), 1)
        self.assertEqual(result["pages"][0]["http_status"], 500)
        self.assertEqual(result["pages"][0]["item_count"], 0)


class JoongnaExtractorTest(unittest.TestCase):
    def test_extracts_normal_product(self):
        candidate = extract_joongna_candidates(json.dumps(_payload([_item()]), ensure_ascii=False))[0]

        self.assertEqual(candidate.raw["product_id"], "123")
        self.assertEqual(candidate.product_name, "Galaxy S25 256GB")
        self.assertEqual(candidate.price, 700000)
        self.assertEqual(candidate.product_url, "https://web.joongna.com/product/123")
        self.assertEqual(candidate.image_url, "https://img2.joongna.com/media/original/item.jpg?impolicy=thumb&size=150")
        self.assertEqual(candidate.source, "joongna")
        self.assertEqual(candidate.condition, "used")
        self.assertEqual(candidate.currency, "KRW")

    def test_preserves_location_and_sort_date_in_raw(self):
        candidate = extract_joongna_candidates(json.dumps(_payload([_item()]), ensure_ascii=False))[0]

        self.assertEqual(candidate.raw["sortDate"], "2026-10-13 10:41:06")
        self.assertEqual(candidate.raw["mainLocationName"], "Innovation-dong")
        self.assertEqual(candidate.raw["locationNames"], ["Jeonju Innovation-dong"])
        self.assertEqual(candidate.raw["storeSeq"], 10530536)

    def test_state_zero_is_available(self):
        candidate = extract_joongna_candidates(json.dumps(_payload([_item(state=0)]), ensure_ascii=False))[0]

        self.assertEqual(candidate.raw["state"], 0)
        self.assertEqual(candidate.raw["sale_status"], "available")

    def test_state_one_is_reserved(self):
        candidate = extract_joongna_candidates(json.dumps(_payload([_item(state=1)]), ensure_ascii=False))[0]

        self.assertEqual(candidate.raw["state"], 1)
        self.assertEqual(candidate.raw["sale_status"], "reserved")

    def test_unconfirmed_state_is_not_mapped(self):
        candidates = extract_joongna_candidates(json.dumps(_payload([_item(seq=2, state=2), _item(seq=3, state=3)]), ensure_ascii=False))

        self.assertEqual([candidate.raw["state"] for candidate in candidates], [2, 3])
        self.assertEqual([candidate.raw["sale_status"] for candidate in candidates], [None, None])

    def test_missing_required_values_are_excluded(self):
        items = [
            _item(seq="", title="Product", price=100),
            _item(seq=2, title="", price=100),
            _item(seq=3, title="Product", price=None),
            _item(seq=4, title="Product", price=-1),
            _item(seq=5, title="Product", price=100, image_url=""),
        ]

        self.assertEqual(extract_joongna_candidates(json.dumps(_payload(items), ensure_ascii=False)), [])

    def test_duplicate_seq_is_deduped(self):
        candidates = extract_joongna_candidates(
            json.dumps(_payload([_item(seq=9, title="Product A"), _item(seq=9, title="Product B")]), ensure_ascii=False)
        )

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].product_name, "Product A")

    def test_page_zero_and_page_one_payloads_are_extracted(self):
        candidates = extract_joongna_candidates(
            _page_payload(
                _page(0, [_item(seq=1)]),
                _page(1, [_item(seq=2)]),
            )
        )

        self.assertEqual([candidate.raw["product_id"] for candidate in candidates], ["1", "2"])

    def test_limit_is_applied(self):
        candidates = extract_joongna_candidates(json.dumps(_payload([_item(seq=index) for index in range(5)])), limit=2)

        self.assertEqual(len(candidates), 2)

    def test_api_http_error_page_is_ignored(self):
        candidates = extract_joongna_candidates(_page_payload(_page(0, [_item()], status=500)))

        self.assertEqual(candidates, [])

    def test_non_success_meta_code_is_ignored(self):
        candidates = extract_joongna_candidates(json.dumps(_payload([_item()], code=400100), ensure_ascii=False))

        self.assertEqual(candidates, [])

    def test_empty_items_returns_empty_list(self):
        self.assertEqual(extract_joongna_candidates(json.dumps(_payload([]), ensure_ascii=False)), [])


if __name__ == "__main__":
    unittest.main()
