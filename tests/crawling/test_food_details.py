import unittest

from crawler_engine.detail_extractors import enrich_candidates_with_food_details, get_detail_extractor
from crawler_engine.food_details import (
    FoodDetail,
    apply_food_detail,
    clean_notice_description,
    html_image_urls,
    html_to_text,
    parse_allergens,
)
from crawler_engine.models import ProductCandidate


class FoodDetailsTest(unittest.TestCase):
    def test_parse_allergens_from_explicit_text(self):
        self.assertEqual(parse_allergens("\uc54c\ub808\ub974\uae30 \uc720\ubc1c\ubb3c\uc9c8: \ub300\ub450, \uc6b0\uc720 \ud568\uc720"), ["\ub300\ub450", "\uc6b0\uc720"])
        self.assertEqual(parse_allergens("\ub300\ub450 \ubc0f \ubcf5\uc22d\uc544"), ["\ub300\ub450", "\ubcf5\uc22d\uc544"])

    def test_parse_allergens_keeps_unknown_as_none(self):
        self.assertIsNone(parse_allergens(""))
        self.assertIsNone(parse_allergens(None))
        self.assertIsNone(parse_allergens("\ud574\ub2f9\uc5c6\uc74c"))

    def test_clean_notice_description_ignores_guidance(self):
        self.assertIsNone(clean_notice_description("\uc0c1\ud488\uc124\uba85 \ubc0f \uc0c1\ud488\uc774\ubbf8\uc9c0 \ucc38\uc870"))
        self.assertEqual(clean_notice_description("\uc720\uae30\ub18d \uc0ac\uacfc\uc2dd\ucd08 100%"), "\uc720\uae30\ub18d \uc0ac\uacfc\uc2dd\ucd08 100%")

    def test_html_helpers(self):
        html = '<p>\uc0ac\uacfc\uc8fc\uc2a4 <b>100%</b></p><img src="https://example.com/label.jpg">'

        self.assertEqual(html_to_text(html), "\uc0ac\uacfc\uc8fc\uc2a4 100%")
        self.assertEqual(html_image_urls(html), ["https://example.com/label.jpg"])

    def test_apply_food_detail_updates_candidate_and_raw_payload(self):
        candidate = ProductCandidate(product_name="\uc0ac\uacfc\uc8fc\uc2a4")
        detail = FoodDetail(
            ingredients="\uc0ac\uacfc\uc8fc\uc2a4 100%",
            allergens=["\ub300\ub450"],
            notice_image_urls=["https://example.com/notice.jpg"],
            detail_image_urls=["https://example.com/detail.jpg"],
            raw={"allergy_text": "\ub300\ub450"},
        )

        apply_food_detail(candidate, detail, source="kurly")

        self.assertEqual(candidate.ingredients, "\uc0ac\uacfc\uc8fc\uc2a4 100%")
        self.assertEqual(candidate.allergens, ["\ub300\ub450"])
        self.assertEqual(candidate.raw["food_detail"]["source"], "kurly")
        self.assertTrue(candidate.raw["food_detail"]["has_food_notice_images"])
        self.assertEqual(candidate.raw["food_detail"]["allergy_text"], "\ub300\ub450")

    def test_detail_registry_ignores_unregistered_sources(self):
        candidate = ProductCandidate(product_name="\uc0ac\uacfc", product_url="https://example.com/product")

        enriched = enrich_candidates_with_food_details(
            [candidate],
            source="example",
            fetch_detail_html=lambda url: (_ for _ in ()).throw(AssertionError("should not fetch")),
            limit=1,
        )

        self.assertIsNone(get_detail_extractor("example"))
        self.assertEqual(enriched, [candidate])
        self.assertEqual(candidate.raw, {})


if __name__ == "__main__":
    unittest.main()
