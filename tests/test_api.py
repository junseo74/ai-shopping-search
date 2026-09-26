import tempfile
import unittest
from pathlib import Path

from backend.main import create_app


class ApiTest(unittest.TestCase):
    def test_collect_search_and_sources(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "products.db"
            app = create_app(db_path)
            routes = {route.path: route.endpoint for route in app.routes}

            try:
                root = routes["/"]()
                collect = routes["/collect/{source_name}"]("test_fixture", limit=4)
                search = routes["/search"](q="Test", limit=50)
                sources = routes["/sources"]()

                self.assertEqual(root["message"], "AI Shopping Search \uc11c\ubc84 \uc2e4\ud589 \uc131\uacf5")
                self.assertEqual(collect.status, "success")
                self.assertEqual(collect.product_count, 4)
                self.assertEqual(len(search), 4)
                self.assertEqual(sources[0]["source_name"], "test_fixture")
                self.assertEqual(sources[0]["product_count"], 4)
            finally:
                del routes
                del app
            db_path.unlink()


if __name__ == "__main__":
    unittest.main()
