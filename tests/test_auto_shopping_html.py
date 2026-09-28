import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import yaml

from backend.tools.auto_shopping_html import AutoShoppingHtmlCollector, load_source_config, write_result_json


class _ShoppingFixtureHandler(BaseHTTPRequestHandler):
    robots_body = "User-agent: *\nAllow: /search\n"
    requests_seen: list[str] = []

    def do_GET(self):
        parsed = urlparse(self.path)
        self.__class__.requests_seen.append(self.path)
        if parsed.path == "/robots.txt":
            self._send(200, self.robots_body)
            return
        if parsed.path == "/search":
            params = parse_qs(parsed.query)
            page = params.get("page", ["1"])[0]
            query = params.get("q", [""])[0]
            self._send(200, self._search_page(query=query, page=page))
            return
        self._send(404, "not found")

    def log_message(self, format, *args):
        return

    def _send(self, status: int, body: str):
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _search_page(self, query: str, page: str) -> str:
        if page == "1":
            return f"""
            <html>
              <body>
                <section data-query="{query}">
                  <article class="product-card">
                    <a class="product-link" href="/products/100?utm_source=fixture">Local Keyboard A</a>
                    <span class="price">49,900원</span>
                    <span class="shipping">배송비 3,000원</span>
                    <span class="seller">Local Mall</span>
                    <img class="image" src="/images/100.jpg" />
                  </article>
                  <article class="product-card">
                    <a class="product-link" href="/products/200">Local Mouse B</a>
                    <span class="price">29,900원</span>
                    <span class="shipping">무료배송</span>
                    <span class="seller">Second Mall</span>
                    <img class="image" src="/images/200.jpg" />
                  </article>
                </section>
              </body>
            </html>
            """
        return f"""
        <html>
          <body>
            <section data-query="{query}">
              <article class="product-card">
                <a class="product-link" href="/products/100?utm_campaign=again">Local Keyboard A Updated</a>
                <span class="price">49,900원</span>
                <span class="shipping">배송비 3,000원</span>
                <span class="seller">Local Mall</span>
                <img class="image" src="/images/100.jpg" />
              </article>
              <article class="product-card">
                <a class="product-link" href="/products/300">Local Stand C</a>
                <span class="price">19,900원</span>
                <span class="shipping">배송비 2,500원</span>
                <span class="seller">Third Mall</span>
              </article>
            </section>
          </body>
        </html>
        """


class AutoShoppingHtmlTest(unittest.TestCase):
    def setUp(self):
        _ShoppingFixtureHandler.requests_seen = []
        _ShoppingFixtureHandler.robots_body = "User-agent: *\nAllow: /search\n"
        self.server = HTTPServer(("127.0.0.1", 0), _ShoppingFixtureHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.thread.join(timeout=2)
        self.server.server_close()

    def test_collects_multiple_pages_and_deduplicates_by_normalized_url(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = self._write_config(temp_dir)
            source = load_source_config(config_path)
            collector = AutoShoppingHtmlCollector(source=source, delay_seconds=0, timeout_seconds=2)
            products, summary = collector.collect(query="keyboard", max_pages=2)
            output_path = Path(temp_dir) / "auto_products.json"
            write_result_json(products, summary, output_path)
            payload = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(summary.requested_pages, 2)
        self.assertEqual(summary.successful_pages, 2)
        self.assertEqual(summary.total_extracted_count, 4)
        self.assertEqual(summary.duplicate_count, 1)
        self.assertEqual(summary.final_product_count, 3)
        self.assertEqual(summary.pages[0].extracted_count, 2)
        self.assertEqual(summary.pages[1].duplicate_count, 1)
        self.assertEqual(summary.missing_fields["image_url"], 1)
        self.assertEqual(payload["summary"]["final_product_count"], 3)
        self.assertEqual(products[0]["source_query"], "keyboard")
        self.assertEqual(products[0]["source_page"], 1)
        self.assertTrue(any(path.startswith("/robots.txt") for path in _ShoppingFixtureHandler.requests_seen))

    def test_records_page_failure_when_robots_disallows_search(self):
        _ShoppingFixtureHandler.robots_body = "User-agent: *\nDisallow: /search\n"
        with tempfile.TemporaryDirectory() as temp_dir:
            source = load_source_config(self._write_config(temp_dir))
            collector = AutoShoppingHtmlCollector(source=source, delay_seconds=0, timeout_seconds=2)
            products, summary = collector.collect(query="keyboard", max_pages=1)

        self.assertEqual(products, [])
        self.assertEqual(summary.successful_pages, 0)
        self.assertEqual(summary.pages[0].status, "failed")
        self.assertIn("robots.txt", summary.pages[0].error_message)

    def test_requires_explicit_permission_in_config(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "sources.yml"
            config_path.write_text(
                yaml.safe_dump(
                    {
                        "sources": [
                            {
                                "name": "local_fixture",
                                "search_url_template": f"{self.base_url}/search?q={{query}}&page={{page}}",
                                "permission": {"approved": False},
                                "selectors": self._selectors(),
                            }
                        ]
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                load_source_config(config_path)

    def _write_config(self, temp_dir: str) -> Path:
        config_path = Path(temp_dir) / "sources.yml"
        config_path.write_text(
            yaml.safe_dump(
                {
                    "sources": [
                        {
                            "name": "local_fixture",
                            "search_url_template": f"{self.base_url}/search?q={{query}}&page={{page}}",
                            "permission": {
                                "approved": True,
                                "note": "Local unittest server fixture only.",
                            },
                            "selectors": self._selectors(),
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
        return config_path

    def _selectors(self) -> dict[str, str]:
        return {
            "product_card": ".product-card",
            "product_name": ".product-link",
            "price": ".price",
            "shipping_fee": ".shipping",
            "seller": ".seller",
            "product_url": ".product-link",
            "image_url": ".image",
        }


if __name__ == "__main__":
    unittest.main()
