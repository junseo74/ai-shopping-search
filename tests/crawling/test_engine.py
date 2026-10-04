import unittest

from crawler_engine.engine import CrawlerEngine
from crawler_engine.models import CrawlRequest
from crawler_engine.sources import select_sources


class StaticEngine(CrawlerEngine):
    def __init__(self, html: str):
        super().__init__()
        self.html = html

    def render_page(self, url: str) -> str:
        return self.html


class FailingEngine(CrawlerEngine):
    def render_page(self, url: str) -> str:
        raise RuntimeError("browser failed")


class EngineTest(unittest.TestCase):
    def test_used_source_is_skipped_when_used_is_disabled(self):
        request = CrawlRequest(query="\uc544\uc774\ud3f0 15", include_used=False)

        self.assertEqual(select_sources(request, "joongna"), [])

    def test_engine_outputs_deduplicated_json_ready_products(self):
        html = """
        <a href="/product/1"><span>\uc544\uc774\ud3f0 15</span><strong>650,000\uc6d0</strong></a>
        <a href="/product/1"><span>\uc544\uc774\ud3f0 15</span><strong>650,000\uc6d0</strong></a>
        """
        result = StaticEngine(html).crawl(
            CrawlRequest(query="\uc544\uc774\ud3f0 15", include_used=True, limit=20),
            source_name="joongna",
        )

        self.assertEqual(len(result.products), 1)
        self.assertEqual(result.products[0].source, "joongna")
        self.assertEqual(result.products[0].price, 650000)
        self.assertIn("products", result.to_dict())

    def test_debug_metrics_are_reported_when_enabled(self):
        html = """
        <html><head><title>fixture</title></head><body>
        <script type="application/ld+json">{"@type":"Thing","name":"not product"}</script>
        <a href="/product/1"><span>\uc544\uc774\ud3f0 15</span><strong>650,000\uc6d0</strong></a>
        </body></html>
        """
        result = StaticEngine(html).crawl(
            CrawlRequest(query="\uc544\uc774\ud3f0 15", include_used=True, limit=20),
            source_name="joongna",
        )

        self.assertEqual(result.debug, {})

        debug_result = StaticEngine(html)
        debug_result.debug = True
        result = debug_result.crawl(
            CrawlRequest(query="\uc544\uc774\ud3f0 15", include_used=True, limit=20),
            source_name="joongna",
        )

        self.assertEqual(result.debug["joongna"]["json_ld_script_count"], 1)
        self.assertEqual(result.debug["joongna"]["total_link_count"], 1)
        self.assertEqual(result.debug["joongna"]["dom_candidate_count"], 1)

    def test_access_error_status_for_obvious_error_page(self):
        html = "<html><head><title>ERROR: The request could not be satisfied</title></head><body>error</body></html>"
        engine = StaticEngine(html)
        engine._last_render_debug = {
            "requested_url": "https://web.joongna.com/search/x",
            "final_url": "https://web.joongna.com/search/x",
            "title": "ERROR: The request could not be satisfied",
            "http_status": 403,
        }

        result = engine.crawl(
            CrawlRequest(query="\uc544\uc774\ud3f0 15", include_used=True, limit=20),
            source_name="joongna",
        )

        self.assertEqual(result.status, "access_error")
        self.assertEqual(result.products, [])
        self.assertIn("Source returned HTTP status 403", result.error)

    def test_no_results_status_for_normal_empty_page(self):
        html = "<html><head><title>No products</title></head><body><a href='/help'>help</a></body></html>"

        result = StaticEngine(html).crawl(
            CrawlRequest(query="\uc5c6\ub294\uc0c1\ud488", include_used=True, limit=20),
            source_name="joongna",
        )

        self.assertEqual(result.status, "no_results")
        self.assertEqual(result.error, None)

    def test_render_error_status_for_browser_failure(self):
        result = FailingEngine().crawl(
            CrawlRequest(query="\uc544\uc774\ud3f0 15", include_used=True, limit=20),
            source_name="joongna",
        )

        self.assertEqual(result.status, "render_error")
        self.assertIn("browser failed", result.error)

    def test_success_status_for_products(self):
        html = """
        <a href="/product/1"><span>\uc544\uc774\ud3f0 15</span><strong>650,000\uc6d0</strong></a>
        """

        result = StaticEngine(html).crawl(
            CrawlRequest(query="\uc544\uc774\ud3f0 15", include_used=True, limit=20),
            source_name="joongna",
        )

        self.assertEqual(result.status, "success")
        self.assertEqual(result.to_dict()["status"], "success")


if __name__ == "__main__":
    unittest.main()
