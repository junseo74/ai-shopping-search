import json
import shutil
import tempfile
import unittest
from pathlib import Path

from backend.tools.merge_shopping_html import (
    ShoppingHtmlMerger,
    discover_html_paths,
    normalize_product_url,
    product_identity_key,
)


class ShoppingHtmlMergerTest(unittest.TestCase):
    def test_merges_multiple_html_files_and_deduplicates_by_normalized_url(self):
        merger = ShoppingHtmlMerger()
        first = Path("tests/fixtures/naver_all_products_next_data_fixture.html")
        second = Path("tests/fixtures/naver_all_products_second_fixture.html")

        products, summary = merger.merge_paths([first, second])

        self.assertEqual(summary.file_count, 2)
        self.assertEqual(summary.total_extracted_count, 7)
        self.assertEqual(summary.duplicate_count, 1)
        self.assertEqual(summary.final_product_count, 6)
        self.assertEqual(summary.files[0].extracted_count, 4)
        self.assertEqual(summary.files[0].source_query, "fixture query")
        self.assertEqual(summary.files[1].extracted_count, 3)
        self.assertEqual(summary.files[1].source_query, "second fixture")
        self.assertEqual(summary.missing_fields["image_url"], 0)

        ad_one_rows = [product for product in products if product["product_name"] == "Fixture Ad Product 1"]
        same_name_organic_rows = [
            product for product in products if product["product_name"] == "Fixture Organic Product 1"
        ]
        self.assertEqual(len(ad_one_rows), 1)
        self.assertEqual(len(same_name_organic_rows), 2)
        self.assertEqual({product["seller"] for product in same_name_organic_rows}, {"Fixture Low Mall", "Different Fixture Mall"})
        self.assertTrue(all(product["source_query"] for product in products))

    def test_discovers_html_files_from_folders_and_writes_import_compatible_json(self):
        merger = ShoppingHtmlMerger()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            shutil.copy(
                Path("tests/fixtures/naver_all_products_next_data_fixture.html"),
                temp_path / "first.html",
            )
            shutil.copy(
                Path("tests/fixtures/naver_all_products_second_fixture.html"),
                temp_path / "second.htm",
            )
            (temp_path / "ignored.txt").write_text("not html", encoding="utf-8")

            discovered = discover_html_paths([temp_path])
            products, summary = merger.merge_paths([temp_path])
            output_path = temp_path / "merged_products.json"
            merger.write_json(products, summary, output_path)
            payload = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(len(discovered), 2)
        self.assertIn("summary", payload)
        self.assertIn("products", payload)
        self.assertEqual(payload["summary"]["final_product_count"], 6)
        self.assertEqual(len(payload["products"]), 6)

    def test_product_identity_does_not_merge_same_name_without_same_url_or_seller(self):
        first = {
            "product_name": "Same Product Name",
            "seller": "Seller A",
            "product_url": "https://example.com/products/1?utm_source=a#section",
        }
        second = {
            "product_name": "Same Product Name",
            "seller": "Seller B",
            "product_url": "https://example.com/products/2?utm_source=a#section",
        }

        self.assertNotEqual(product_identity_key(first), product_identity_key(second))
        self.assertEqual(
            normalize_product_url("https://EXAMPLE.com/products/1?utm_source=a&color=black#section"),
            "https://example.com/products/1?color=black",
        )

    def test_product_identity_does_not_merge_by_name_only_across_files(self):
        first = {
            "product_name": "Same Product Name",
            "source_file": "first.html",
        }
        second = {
            "product_name": "Same Product Name",
            "source_file": "second.html",
        }

        self.assertNotEqual(product_identity_key(first), product_identity_key(second))

    def test_product_identity_merges_same_smartstore_product_id_with_different_titles(self):
        first = {
            "product_name": "국내매장판 나이키 올블랙운동화 남성러닝화",
            "seller": "메이커 쇼핑",
            "product_url": "https://smartstore.naver.com/main/products/8372501932",
        }
        second = {
            "product_name": "나이키 올블랙운동화 검정운동화 남성러닝화 300까지 사계절용",
            "seller": "메이커 쇼핑",
            "product_url": "https://smartstore.naver.com/main/products/8372501932",
        }

        self.assertEqual(product_identity_key(first), product_identity_key(second))
        self.assertEqual(product_identity_key(first), ("product_id", "smartstore.naver.com:products:8372501932"))


if __name__ == "__main__":
    unittest.main()
