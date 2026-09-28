import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import create_app
from backend.tools.import_saved_naver_products import import_saved_naver_products


class SavedNaverImportTest(unittest.TestCase):
    def test_import_saved_json_and_skip_duplicate_product_urls(self):
        rows = [
            {
                "product_name": "Fixture Naver Ad One",
                "price": 69900,
                "original_price": 109000,
                "shipping_fee": 4000,
                "seller": "Fixture Store",
                "product_url": "https://ad.example/one?c=nshop.npla&t=0",
                "image_url": "https://shopping-phinf.pstatic.net/fixture/one.jpg",
            },
            {
                "product_name": "Fixture Naver Ad Two",
                "price": 59900,
                "original_price": 99000,
                "shipping_fee": 0,
                "seller": "Fixture Store",
                "product_url": "https://ad.example/two?c=nshop.npla&t=0",
                "image_url": "https://shopping-phinf.pstatic.net/fixture/two.jpg",
            },
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            json_path = Path(temp_dir) / "naver_products.json"
            json_path.write_text(json.dumps(rows), encoding="utf-8")
            db_path = Path(temp_dir) / "products.db"
            source_url = "https://search.shopping.naver.com/search/all?query=fixture"
            observed_at = datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc)

            first = import_saved_naver_products(
                file_path=json_path,
                db_path=db_path,
                source_url=source_url,
                source_observed_at=observed_at,
            )
            second = import_saved_naver_products(
                file_path=json_path,
                db_path=db_path,
                source_url=source_url,
                source_observed_at=observed_at,
            )

            self.assertEqual(first["saved_count"], 2)
            self.assertEqual(second["saved_count"], 0)
            self.assertEqual(second["skipped_count"], 2)

            app = create_app(db_path)
            client = TestClient(app)
            products_response = client.get(
                "/products",
                params={"limit": 10, "data_source": "saved_html_import"},
            )
            search_response = client.get(
                "/search",
                params={"q": "Naver Ad One", "limit": 10},
            )

            self.assertEqual(products_response.status_code, 200)
            self.assertEqual(search_response.status_code, 200)
            products = products_response.json()
            searched = search_response.json()
            first_product = next(product for product in products if product["product_name"] == "Fixture Naver Ad One")
            self.assertEqual(len(products), 2)
            self.assertEqual(first_product["platform"], "naver_shopping")
            self.assertEqual(first_product["data_source"], "saved_html_import")
            self.assertEqual(first_product["source_url"], source_url)
            observed_response = datetime.fromisoformat(first_product["source_observed_at"].replace("Z", "+00:00"))
            self.assertEqual(observed_response, observed_at)
            self.assertEqual(first_product["original_price"], 109000.0)
            self.assertEqual(len(searched), 1)
            self.assertEqual(searched[0]["product_name"], "Fixture Naver Ad One")


if __name__ == "__main__":
    unittest.main()
