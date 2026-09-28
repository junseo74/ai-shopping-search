import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from backend.collectors import HtmlListSiteConfig, HtmlProductListParser, ShoppingAutoCollector
from backend.models import PlatformType, Product, ProductCondition


class StubApiCollector:
    def collect(self, query=None, limit=20):
        return [
            Product(
                product_name="Fixture API Runner",
                price=99000.0,
                currency="KRW",
                seller="Fixture API Seller",
                platform=PlatformType.SHOPPING_MALL,
                product_url="https://example.com/products/fixture-runner-2",
                image_url="https://cdn.example.com/fixture-runner-2-api.jpg",
                condition=ProductCondition.NEW,
                data_source="stub_api",
            ),
            Product(
                product_name="Fixture API Backpack",
                price=59000.0,
                currency="KRW",
                seller="Fixture API Seller",
                platform=PlatformType.SHOPPING_MALL,
                product_url="https://api.example.com/products/fixture-backpack",
                image_url="https://api.example.com/images/fixture-backpack.jpg",
                condition=ProductCondition.NEW,
                data_source="stub_api",
            ),
        ][:limit]


class ShoppingAutoCollectorTest(unittest.TestCase):
    def test_naver_shopping_fixture_parser_extracts_core_fields_without_real_selectors(self):
        html = Path("tests/fixtures/naver_shopping_search_fixture.html").read_text(encoding="utf-8")
        site_config = HtmlListSiteConfig(
            name="naver_shopping_fixture",
            domains=("search.shopping.naver.com",),
            selectors={
                "product_card": "[data-naver-fixture-card='product']",
                "product_name": "[data-naver-fixture-field='name']",
                "price": "[data-naver-fixture-field='price']",
                "seller": "[data-naver-fixture-field='seller']",
                "product_url": "[data-naver-fixture-field='url']",
                "image_url": "[data-naver-fixture-field='image']",
            },
            attributes={"product_url": "href", "image_url": "src"},
            permission_note="Local Naver Shopping parser fixture only. These are not real selectors.",
        )

        products = HtmlProductListParser().parse(
            html,
            source_url="https://search.shopping.naver.com/search/all?query=keyboard",
            site_config=site_config,
            limit=20,
        )

        self.assertEqual(len(products), 2)
        self.assertEqual(products[0].product_name, "Fixture Naver Keyboard")
        self.assertEqual(products[0].price, 49900.0)
        self.assertEqual(products[0].seller, "Fixture Smart Store A")
        self.assertEqual(str(products[0].product_url), "https://search.shopping.naver.com/catalog/fixture-naver-keyboard")
        self.assertEqual(str(products[0].image_url), "https://shopping-phinf.pstatic.net/fixture-keyboard.jpg")
        self.assertEqual(products[1].product_name, "Fixture Naver Monitor")
        self.assertEqual(products[1].price, 199000.0)
        self.assertEqual(str(products[1].product_url), "https://shopping.example.test/catalog/fixture-naver-monitor")
        self.assertEqual(str(products[1].image_url), "https://shopping-phinf.pstatic.net/fixture-monitor.jpg")
        self.assertEqual(len({str(product.product_url) for product in products}), 2)

    def test_naver_shopping_fixture_keeps_query_flow_in_shopping_auto_without_network(self):
        html = Path("tests/fixtures/naver_shopping_search_fixture.html").read_text(encoding="utf-8")
        requested_urls = []

        def fetcher(url):
            requested_urls.append(url)
            return html

        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "naver_shopping_fixture_sources.yml"
            config_path.write_text(
                """
sources:
  - name: naver_shopping_fixture
    collection_method: approved_html
    seller: null
    list_urls:
      - https://naver-shopping-fixture.example/search?query={query}
    permission:
      approved: true
      note: Local Naver Shopping fixture only. Not real collection permission.
    selectors:
      product_card: "[data-naver-fixture-card='product']"
      product_name: "[data-naver-fixture-field='name']"
      price: "[data-naver-fixture-field='price']"
      seller: "[data-naver-fixture-field='seller']"
      product_url: "[data-naver-fixture-field='url']"
      image_url: "[data-naver-fixture-field='image']"
    attributes:
      product_url: "href"
      image_url: "src"
""",
                encoding="utf-8",
            )

            with patch.dict("os.environ", {"SHOPPING_AUTO_DELAY_SECONDS": "0"}, clear=False):
                collector = ShoppingAutoCollector(
                    config_path=config_path,
                    html_fetcher=fetcher,
                    robots_checker=lambda url: None,
                )
                products = collector.collect(query="무선 키보드", limit=5)

        self.assertEqual(
            requested_urls,
            ["https://naver-shopping-fixture.example/search?query=%EB%AC%B4%EC%84%A0+%ED%82%A4%EB%B3%B4%EB%93%9C"],
        )
        self.assertEqual([product.product_name for product in products], ["Fixture Naver Keyboard", "Fixture Naver Monitor"])
        self.assertEqual([product.data_source for product in products], ["naver_shopping_fixture", "naver_shopping_fixture"])
        self.assertEqual(collector.last_failures, [])

    def test_default_naver_shopping_reference_is_not_approved_and_does_not_request_network(self):
        requested_urls = []

        with patch.dict("os.environ", {"SHOPPING_AUTO_DELAY_SECONDS": "0"}, clear=False):
            collector = ShoppingAutoCollector(
                html_fetcher=lambda url: requested_urls.append(url) or "",
                robots_checker=lambda url: requested_urls.append(url),
            )
            products = collector.collect(query="keyboard", limit=5)

        self.assertEqual(products, [])
        self.assertEqual(collector.approved_source_count(), 0)
        self.assertEqual(requested_urls, [])

    def test_collects_approved_sources_deduplicates_and_records_failures_without_network(self):
        html = Path("tests/fixtures/approved_html_list.html").read_text(encoding="utf-8")
        requested_urls = []
        robots_checked = []

        def fetcher(url):
            requested_urls.append(url)
            if "failing.example.com" in url:
                raise RuntimeError("fixture fetch failed")
            return html

        def robots_checker(url):
            robots_checked.append(url)

        with patch.dict("os.environ", {"SHOPPING_AUTO_DELAY_SECONDS": "0"}, clear=False):
            collector = ShoppingAutoCollector(
                config_path=Path("tests/fixtures/shopping_auto_sources.yml"),
                html_fetcher=fetcher,
                robots_checker=robots_checker,
            )

            products = collector.collect(query="running shoes", limit=20)

        self.assertEqual([product.product_name for product in products], ["Fixture Runner 1", "Fixture Runner 2"])
        self.assertEqual(str(products[0].product_url), "https://example.com/products/fixture-runner-1")
        self.assertEqual(str(products[0].image_url), "https://example.com/images/fixture-runner-1.jpg")
        self.assertEqual(products[0].seller, "Fixture Seller")
        self.assertEqual(products[0].data_source, "fixture_html_shop")
        self.assertEqual(len({str(product.product_url) for product in products}), 2)
        self.assertEqual(len(collector.last_failures), 1)
        self.assertEqual(collector.last_failures[0].source_name, "fixture_failing_shop")
        self.assertIn("fixture fetch failed", collector.last_failures[0].error_message)
        self.assertEqual(
            requested_urls,
            [
                "https://example.com/search?q=running+shoes",
                "https://failing.example.com/search?q=running+shoes",
            ],
        )
        self.assertNotIn("https://www.nike.com/kr/w/shoes", requested_urls)
        self.assertEqual(requested_urls, robots_checked)

    def test_api_sources_can_merge_with_html_and_deduplicate_by_product_url(self):
        html = Path("tests/fixtures/approved_html_list.html").read_text(encoding="utf-8")
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "shopping_auto_api_sources.yml"
            config_path.write_text(
                """
sources:
  - name: fixture_html_shop
    collection_method: approved_html
    seller: Fixture Seller
    list_urls:
      - https://example.com/search?q={query}
    permission:
      approved: true
      note: Local unit test fixture only.
    selectors:
      product_card: ".product-card"
      product_name: "[data-fixture-field='name']"
      price: "[data-fixture-field='price']"
      product_url: "[data-fixture-field='url']"
      image_url: ".product-card__hero-image"
    attributes:
      product_url: "href"
      image_url: "src"
  - name: fixture_api_shop
    collection_method: api
    seller: Fixture API Seller
    api_collector: stub_api
    permission:
      approved: true
      note: Local unit test fixture only.
""",
                encoding="utf-8",
            )

            with patch.dict("os.environ", {"SHOPPING_AUTO_DELAY_SECONDS": "0"}, clear=False):
                collector = ShoppingAutoCollector(
                    config_path=config_path,
                    api_collectors={"stub_api": StubApiCollector()},
                    html_fetcher=lambda url: html,
                    robots_checker=lambda url: None,
                )

                products = collector.collect(query="runner", limit=20)

            self.assertEqual(
                [str(product.product_url) for product in products],
                [
                    "https://example.com/products/fixture-runner-1",
                    "https://example.com/products/fixture-runner-2",
                    "https://api.example.com/products/fixture-backpack",
                ],
            )
            self.assertEqual(products[-1].data_source, "fixture_api_shop")
            self.assertEqual(collector.last_failures, [])


if __name__ == "__main__":
    unittest.main()
