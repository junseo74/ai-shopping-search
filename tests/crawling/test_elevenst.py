import json
import unittest
from urllib.parse import parse_qs, urlparse

from crawler_engine.extractors.elevenst import extract_elevenst_candidates
from crawler_engine.models import CrawlRequest
from crawler_engine.sources import available_sources, select_sources


def _item(
    product_id="123",
    title="\uac24\ub7ed\uc2dc S25 256GB",
    final_prc="429,990",
    sel_prc="440,900",
    link_url="//m.11st.co.kr/products/123",
    image_url="//cdn.011st.com/image/123.jpg",
    extra=None,
):
    item = {
        "id": product_id,
        "title": title,
        "finalPrc": final_prc,
        "selPrc": sel_prc,
        "linkUrl": link_url,
        "imageUrl": image_url,
    }
    if extra:
        item.update(extra)
    return item


def _payload_at(index: int, items: list[dict]):
    data = [{"tab": f"tab-{number}", "items": []} for number in range(index + 1)]
    data[index]["items"] = items
    return json.dumps({"data": data}, ensure_ascii=False)


class ElevenStSourceTest(unittest.TestCase):
    def test_source_url_and_metadata(self):
        source = available_sources()["elevenst"]
        url = source.build_search_url(CrawlRequest(query="\uac24\ub7ed\uc2dc S25"))
        parsed = urlparse(url)
        query = parse_qs(parsed.query)

        self.assertEqual(parsed.scheme, "https")
        self.assertEqual(parsed.netloc, "apis.11st.co.kr")
        self.assertEqual(parsed.path, "/search/api/tab")
        self.assertEqual(query["poc"], ["mw"])
        self.assertEqual(query["tabId"], ["TOTAL_SEARCH"])
        self.assertEqual(query["tier"], ["A"])
        self.assertEqual(query["searchKeyword"], ["\uac24\ub7ed\uc2dc S25"])
        self.assertEqual(query["pageNo"], ["1"])
        self.assertIn("_", query)
        self.assertEqual(source.metadata.source, "elevenst")
        self.assertEqual(source.metadata.display_name, "11st")
        self.assertEqual(source.metadata.default_condition, "new")

    def test_source_runs_when_used_is_disabled(self):
        selected = select_sources(CrawlRequest(query="\uac24\ub7ed\uc2dc S25", include_used=False), "elevenst")

        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0].metadata.source, "elevenst")


class ElevenStExtractorTest(unittest.TestCase):
    def test_extracts_normal_product(self):
        candidate = extract_elevenst_candidates(_payload_at(5, [_item()]))[0]

        self.assertEqual(candidate.raw["product_id"], "123")
        self.assertEqual(candidate.product_name, "\uac24\ub7ed\uc2dc S25 256GB")
        self.assertEqual(candidate.price, 429990)
        self.assertEqual(candidate.product_url, "https://m.11st.co.kr/products/123")
        self.assertEqual(candidate.image_url, "https://cdn.011st.com/image/123.jpg")
        self.assertEqual(candidate.source, "elevenst")
        self.assertEqual(candidate.condition, "new")
        self.assertEqual(candidate.currency, "KRW")

    def test_final_prc_price_mapping(self):
        candidate = extract_elevenst_candidates(_payload_at(1, [_item(final_prc="1,234", sel_prc="9,999")]))[0]

        self.assertEqual(candidate.price, 1234)

    def test_final_prc_fallback_to_sel_prc(self):
        candidate = extract_elevenst_candidates(_payload_at(1, [_item(final_prc="", sel_prc="9,999")]))[0]

        self.assertEqual(candidate.price, 9999)

    def test_zero_final_prc_fallback_to_sel_prc(self):
        candidate = extract_elevenst_candidates(_payload_at(1, [_item(final_prc="0", sel_prc="9,999")]))[0]

        self.assertEqual(candidate.price, 9999)

    def test_protocol_relative_link_url_and_image_url(self):
        candidate = extract_elevenst_candidates(
            _payload_at(1, [_item(link_url="//m.11st.co.kr/products/abc", image_url="//cdn.011st.com/image/abc.jpg")])
        )[0]

        self.assertEqual(candidate.product_url, "https://m.11st.co.kr/products/abc")
        self.assertEqual(candidate.image_url, "https://cdn.011st.com/image/abc.jpg")

    def test_missing_required_values_are_excluded(self):
        items = [
            _item(product_id="", title="\uc0c1\ud488", final_prc="100", link_url="//m.11st.co.kr/a", image_url="//cdn.011st.com/a.jpg"),
            _item(product_id="2", title="", final_prc="100", link_url="//m.11st.co.kr/b", image_url="//cdn.011st.com/b.jpg"),
            _item(product_id="3", title="\uc0c1\ud488", final_prc="", sel_prc="", link_url="//m.11st.co.kr/c", image_url="//cdn.011st.com/c.jpg"),
            _item(product_id="4", title="\uc0c1\ud488", final_prc="100", link_url="", image_url="//cdn.011st.com/d.jpg"),
            _item(product_id="5", title="\uc0c1\ud488", final_prc="100", link_url="//m.11st.co.kr/e", image_url=""),
        ]

        self.assertEqual(extract_elevenst_candidates(_payload_at(1, items)), [])

    def test_finds_items_at_different_data_positions(self):
        page1 = extract_elevenst_candidates(_payload_at(5, [_item(product_id="p1")]))
        page2 = extract_elevenst_candidates(_payload_at(1, [_item(product_id="p2")]))

        self.assertEqual(page1[0].raw["product_id"], "p1")
        self.assertEqual(page2[0].raw["product_id"], "p2")

    def test_duplicate_product_id_is_deduped(self):
        candidates = extract_elevenst_candidates(
            _payload_at(1, [_item(product_id="dup", title="\uc0c1\ud488 A"), _item(product_id="dup", title="\uc0c1\ud488 B")])
        )

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].product_name, "\uc0c1\ud488 A")

    def test_keeps_one_hundred_won_price(self):
        candidate = extract_elevenst_candidates(_payload_at(1, [_item(product_id="100", final_prc="100", sel_prc="100")]))[0]

        self.assertEqual(candidate.price, 100)


if __name__ == "__main__":
    unittest.main()
