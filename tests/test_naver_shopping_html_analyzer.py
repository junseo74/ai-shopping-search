import json
import tempfile
import unittest
from pathlib import Path

import yaml

from backend.tools.naver_shopping_html_analyzer import NaverShoppingHtmlAnalyzer


class NaverShoppingHtmlAnalyzerTest(unittest.TestCase):
    def test_analyzes_saved_html_selector_candidates_without_network(self):
        analyzer = NaverShoppingHtmlAnalyzer()
        result = analyzer.analyze_file(
            Path("tests/fixtures/naver_shopping_search_fixture.html"),
            source_url="https://search.shopping.naver.com/search/all?query={query}",
            max_candidates=12,
        )

        card = self._candidate(result.card_candidates, "[data-naver-fixture-card='product']")
        self.assertEqual(card.match_count, 5)
        self.assertEqual(card.matching_cards, 5)

        name = self._candidate(result.field_candidates["product_name"], "[data-naver-fixture-field='name']")
        price = self._candidate(result.field_candidates["price"], "[data-naver-fixture-field='price']")
        seller = self._candidate(result.field_candidates["seller"], "[data-naver-fixture-field='seller']")
        product_url = self._candidate(result.field_candidates["product_url"], "[data-naver-fixture-field='url']")
        image_url = self._candidate(result.field_candidates["image_url"], "[data-naver-fixture-field='image']")

        self.assertEqual(name.matching_cards, 4)
        self.assertEqual(price.matching_cards, 4)
        self.assertEqual(seller.matching_cards, 5)
        self.assertEqual(product_url.matching_cards, 5)
        self.assertEqual(image_url.matching_cards, 5)
        self.assertIn("Fixture Naver Keyboard", name.sample_values)
        self.assertTrue(any(value.startswith("49,900") for value in price.sample_values))

    def test_builds_non_approved_draft_config_with_candidates_not_confirmed_selectors(self):
        analyzer = NaverShoppingHtmlAnalyzer()
        result = analyzer.analyze_file(Path("tests/fixtures/naver_shopping_search_fixture.html"))

        draft = analyzer.build_draft_config(result)
        source = draft["sources"][0]

        self.assertFalse(source["permission"]["approved"])
        self.assertEqual(source["selectors"], {})
        self.assertEqual(source["attributes"], {})
        self.assertIn("selector_candidates", source)
        self.assertIn("product_card", source["selector_candidates"])

    def test_writes_non_approved_yaml_draft(self):
        analyzer = NaverShoppingHtmlAnalyzer()
        result = analyzer.analyze_file(Path("tests/fixtures/naver_shopping_search_fixture.html"))

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "naver_draft.yml"
            analyzer.write_draft_config(result, output_path)
            draft = yaml.safe_load(output_path.read_text(encoding="utf-8"))

        source = draft["sources"][0]
        self.assertFalse(source["permission"]["approved"])
        self.assertEqual(source["selectors"], {})
        self.assertGreaterEqual(len(source["selector_candidates"]["product_card"]), 1)

    def test_extracts_confirmed_naver_ad_products_and_writes_json(self):
        analyzer = NaverShoppingHtmlAnalyzer()
        products = analyzer.extract_ad_products_file(
            Path("tests/fixtures/naver_ad_products_confirmed_fixture.html"),
            source_url="https://search.shopping.naver.com/search/all?query=fixture",
        )

        self.assertEqual(len(products), 2)
        self.assertEqual(products[0].product_name, "Fixture Ad Product 1")
        self.assertEqual(products[0].price, 69900.0)
        self.assertEqual(products[0].original_price, 109000.0)
        self.assertEqual(products[0].shipping_fee, 4000.0)
        self.assertEqual(products[0].seller, "Fixture Mall A")
        self.assertEqual(products[0].product_url, "https://search.shopping.naver.com/ad/item-1")
        self.assertEqual(products[0].image_url, "https://shopping-phinf.pstatic.net/main_fixture/item-1.jpg")
        self.assertEqual(products[1].shipping_fee, 0.0)
        self.assertEqual(products[1].image_url, "https://shopping-phinf.pstatic.net/main_fixture/item-2.jpg")

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "products.json"
            analyzer.write_extracted_products_json(products, output_path)
            self.assertIn("Fixture Ad Product 1", output_path.read_text(encoding="utf-8"))

    def test_extracts_all_products_from_next_data_and_summarizes_quality(self):
        analyzer = NaverShoppingHtmlAnalyzer()
        source_url = "https://search.shopping.naver.com/search/all?query=fixture"

        products, summary = analyzer.extract_all_products_file(
            Path("tests/fixtures/naver_all_products_next_data_fixture.html"),
            source_url=source_url,
        )

        self.assertEqual(summary.total_before_dedup, 5)
        self.assertEqual(summary.total_after_dedup, 4)
        self.assertEqual(summary.ad_count, 2)
        self.assertEqual(summary.organic_count, 2)
        self.assertEqual(summary.duplicate_count, 1)
        self.assertEqual(summary.missing_fields["product_url"], 1)
        self.assertEqual(summary.missing_fields["seller"], 1)
        self.assertEqual(summary.missing_fields["image_url"], 0)

        names = [product.product_name for product in products]
        self.assertEqual(names.count("Fixture Organic Product 1"), 1)
        self.assertEqual(products[0].product_type, "ad")
        self.assertEqual(products[0].product_url, "https://search.shopping.naver.com/ad/item-1")
        self.assertEqual(products[1].image_url, "https://shopping-phinf.pstatic.net/main_fixture/item-2.jpg")

        organic = next(product for product in products if product.product_name == "Fixture Organic Product 1")
        self.assertEqual(organic.product_type, "organic")
        self.assertEqual(organic.seller, "Fixture Low Mall")
        self.assertEqual(organic.product_url, "https://search.shopping.naver.com/catalog/organic-1")

    def test_writes_all_products_result_json_compatible_with_importer_shape(self):
        analyzer = NaverShoppingHtmlAnalyzer()
        products, summary = analyzer.extract_all_products_file(
            Path("tests/fixtures/naver_all_products_next_data_fixture.html")
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "all_products.json"
            analyzer.write_extraction_result_json(products, summary, output_path)
            payload = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(payload["summary"]["total_after_dedup"], 4)
        self.assertEqual(len(payload["products"]), 4)
        self.assertEqual(payload["products"][0]["product_type"], "ad")
        self.assertEqual(
            payload["products"][0]["source_url"],
            "https://search.shopping.naver.com/search/all?query=fixture%20query",
        )
        self.assertEqual(payload["products"][2]["product_type"], "organic")

    def _candidate(self, candidates, selector):
        for candidate in candidates:
            if candidate.selector == selector:
                return candidate
        self.fail(f"Missing selector candidate: {selector}")


if __name__ == "__main__":
    unittest.main()
