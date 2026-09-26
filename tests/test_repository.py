import tempfile
import unittest
from pathlib import Path

from backend.collectors import TestFixtureCollector
from backend.db import ProductRepository


class ProductRepositoryTest(unittest.TestCase):
    def test_add_list_and_search_products(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "products.db"
            repository = ProductRepository(db_path)
            try:
                products = TestFixtureCollector().collect(limit=2)

                saved = repository.add_products(products)
                listed = repository.list_products()
                searched = repository.search_products("Laptop")

                self.assertEqual(len(saved), 2)
                self.assertEqual(len(listed), 2)
                self.assertEqual(len(searched), 1)
                self.assertEqual(searched[0].product_name, "Test used laptop")
            finally:
                del repository
            db_path.unlink()


if __name__ == "__main__":
    unittest.main()
