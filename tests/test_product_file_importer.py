import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from backend.db import ProductRepository
from backend.importers import ProductFileImporter


class ProductFileImporterTest(unittest.TestCase):
    def test_import_csv_with_source_metadata(self):
        csv_text = "\n".join(
            [
                "product_name,price,seller,description,product_url",
                "Dataset Product A,12000,Dataset Seller,Old public dataset row,https://example.com/a",
                "Dataset Product B,15000,,Missing seller is preserved,https://example.com/b",
            ]
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "products.csv"
            path.write_text(csv_text, encoding="utf-8")

            products = ProductFileImporter().load(
                file_path=path,
                data_source="unit_dataset",
                source_url="https://example.com/dataset",
                source_license="CC BY 4.0",
                source_observed_at=datetime.fromisoformat("2025-01-01T00:00:00+00:00"),
            )
            repository = ProductRepository(Path(temp_dir) / "products.db")
            saved = repository.add_products(products)
            listed = repository.list_products(data_source="unit_dataset")

            self.assertEqual(len(saved), 2)
            self.assertEqual(len(listed), 2)
            self.assertEqual(listed[0].source_license, "CC BY 4.0")
            self.assertIsNone(listed[0].seller)


if __name__ == "__main__":
    unittest.main()
