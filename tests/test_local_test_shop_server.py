import threading
import tempfile
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

import requests
import yaml

from backend.tools.local_test_shop_server import LocalTestShopHandler
from backend.tools.auto_shopping_html import AutoShoppingHtmlCollector, load_source_config


class LocalTestShopServerTest(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), LocalTestShopHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.thread.join(timeout=2)
        self.server.server_close()

    def test_serves_robots_and_three_search_pages_matching_auto_selectors(self):
        robots = requests.get(f"{self.base_url}/robots.txt", timeout=2)
        page1 = requests.get(f"{self.base_url}/search?q=keyboard&page=1", timeout=2)
        page2 = requests.get(f"{self.base_url}/search?q=keyboard&page=2", timeout=2)
        page3 = requests.get(f"{self.base_url}/search?q=keyboard&page=3", timeout=2)

        self.assertEqual(robots.status_code, 200)
        self.assertIn("Allow: /search", robots.text)
        self.assertEqual(page1.text.count('class="product-card"'), 3)
        self.assertEqual(page2.text.count('class="product-card"'), 3)
        self.assertEqual(page3.text.count('class="product-card"'), 2)
        self.assertIn('class="product-link"', page1.text)
        self.assertIn('class="price"', page1.text)
        self.assertIn('class="shipping"', page1.text)
        self.assertIn('class="seller"', page1.text)
        self.assertIn('class="image"', page1.text)
        self.assertIn("/products/100?utm_source=local", page1.text)
        self.assertIn("/products/100?utm_campaign=again", page2.text)
        self.assertIn("/products/300?utm_source=page3", page3.text)

    def test_auto_collector_runs_against_local_server_end_to_end(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "local_auto_html_sources.yml"
            config_path.write_text(
                yaml.safe_dump(
                    {
                        "sources": [
                            {
                                "name": "local_test_shop",
                                "search_url_template": f"{self.base_url}/search?q={{query}}&page={{page}}",
                                "permission": {
                                    "approved": True,
                                    "note": "Local test server only.",
                                },
                                "selectors": {
                                    "product_card": ".product-card",
                                    "product_name": ".product-link",
                                    "price": ".price",
                                    "shipping_fee": ".shipping",
                                    "seller": ".seller",
                                    "product_url": ".product-link",
                                    "image_url": ".image",
                                },
                                "attributes": {
                                    "product_url": "href",
                                    "image_url": "src",
                                },
                            }
                        ]
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            source = load_source_config(config_path)
            collector = AutoShoppingHtmlCollector(source=source, delay_seconds=0, timeout_seconds=2)
            products, summary = collector.collect(query="keyboard", max_pages=3)

        self.assertEqual(summary.total_extracted_count, 8)
        self.assertEqual(summary.duplicate_count, 2)
        self.assertEqual(summary.final_product_count, 6)
        self.assertEqual(summary.successful_pages, 3)
        self.assertEqual(summary.missing_fields["image_url"], 0)
        self.assertEqual(len(products), 6)


if __name__ == "__main__":
    unittest.main()
