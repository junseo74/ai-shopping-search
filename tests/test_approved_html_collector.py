import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from backend.collectors import ApprovedHtmlProductCollector, HtmlListSiteConfig, HtmlProductListParser, HtmlProductParser


class HtmlProductParserTest(unittest.TestCase):
    def test_parse_product_meta_fields(self):
        html = """
        <html>
          <head>
            <meta property="og:title" content="Example Korean Product" />
            <meta property="product:price:amount" content="12900" />
            <meta name="seller" content="Example Seller" />
            <meta property="og:description" content="A concise product description." />
            <meta property="og:image" content="https://example.com/product.jpg" />
          </head>
          <body>\ubc30\uc1a1\ube44 3,000\uc6d0</body>
        </html>
        """

        product = HtmlProductParser().parse(html)

        self.assertEqual(product.product_name, "Example Korean Product")
        self.assertEqual(product.price, 12900.0)
        self.assertEqual(product.shipping_fee, 3000.0)
        self.assertEqual(product.seller, "Example Seller")
        self.assertEqual(product.detail_description, "A concise product description.")
        self.assertEqual(product.image_url, "https://example.com/product.jpg")

    def test_missing_fields_remain_none(self):
        product = HtmlProductParser().parse("<html><body><h1>Only Name</h1></body></html>")

        self.assertEqual(product.product_name, "Only Name")
        self.assertIsNone(product.price)
        self.assertIsNone(product.shipping_fee)
        self.assertIsNone(product.seller)
        self.assertIsNone(product.detail_description)


class HtmlProductListParserTest(unittest.TestCase):
    def test_parse_listing_cards_with_absolute_urls_and_deduplication(self):
        html = Path("tests/fixtures/approved_html_list.html").read_text(encoding="utf-8")
        site_config = HtmlListSiteConfig(
            name="fixture_shop",
            domains=("example.com",),
            selectors={
                "product_card": ".product-card",
                "product_name": "[data-fixture-field='name']",
                "price": "[data-fixture-field='price']",
                "product_url": "[data-fixture-field='url']",
                "image_url": ".product-card__hero-image",
            },
            attributes={"product_url": "href", "image_url": "src"},
            default_seller="Fixture Seller",
            permission_note="Local parser unit test fixture only.",
        )

        products = HtmlProductListParser().parse(
            html,
            source_url="https://example.com/list?page=1",
            site_config=site_config,
            limit=20,
        )

        self.assertEqual(len(products), 2)
        self.assertEqual(products[0].product_name, "Fixture Runner 1")
        self.assertEqual(products[0].price, 129000.0)
        self.assertEqual(products[0].seller, "Fixture Seller")
        self.assertEqual(str(products[0].product_url), "https://example.com/products/fixture-runner-1")
        self.assertEqual(str(products[0].image_url), "https://example.com/images/fixture-runner-1.jpg")
        self.assertEqual(products[1].product_name, "Fixture Runner 2")
        self.assertEqual(products[1].price, 89500.0)
        self.assertEqual(str(products[1].product_url), "https://example.com/products/fixture-runner-2")
        self.assertEqual(str(products[1].image_url), "https://cdn.example.com/fixture-runner-2.jpg")
        self.assertEqual(str(products[0].source_url), "https://example.com/list?page=1")
        self.assertEqual(products[0].data_source, "approved_html")

    def test_collect_uses_configured_list_urls_and_never_query_urls(self):
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "selectors.yml"
            config_path.write_text(
                """
sites:
  - name: fixture_shop
    domains:
      - example.com
    permission:
      approved: true
      note: Local unit test fixture only.
    default_seller: Fixture Seller
    selectors:
      product_card: ".product-card"
      product_name: "[data-fixture-field='name']"
      price: "[data-fixture-field='price']"
      product_url: "[data-fixture-field='url']"
      image_url: ".product-card__hero-image"
    attributes:
      product_url: "href"
      image_url: "src"
""",
                encoding="utf-8",
            )
            html = Path("tests/fixtures/approved_html_list.html").read_text(encoding="utf-8")

            with patch.dict(
                "os.environ",
                {"APPROVED_HTML_LIST_URLS": "https://example.com/list", "APPROVED_HTML_DELAY_SECONDS": "0"},
                clear=False,
            ):
                collector = ApprovedHtmlProductCollector(selector_config_path=config_path)
                with self.assertRaises(ValueError):
                    collector.collect(query="https://example.com/other", limit=1)

                with patch.object(collector, "_ensure_allowed_by_robots") as robots, patch.object(
                    collector,
                    "_fetch",
                    return_value=html,
                ) as fetch:
                    products = collector.collect(limit=1)

            robots.assert_called_once_with("https://example.com/list")
            fetch.assert_called_once_with("https://example.com/list")
            self.assertEqual(len(products), 1)
            self.assertEqual(products[0].product_name, "Fixture Runner 1")

    def test_collector_requires_explicit_permission_config(self):
        with patch.dict("os.environ", {"APPROVED_HTML_LIST_URLS": "https://example.com/list"}, clear=False):
            collector = ApprovedHtmlProductCollector(selector_config_path=Path("tests/fixtures/missing.yml"))

        with self.assertRaises(RuntimeError):
            collector.collect(limit=1)

    def test_nike_permission_config_stays_disabled_and_does_not_request_network(self):
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "selectors.yml"
            config_path.write_text(
                """
sites:
  - name: nike_unapproved
    domains:
      - nike.com
    permission:
      approved: false
      note: Not approved for automated collection.
    default_seller: Nike
    selectors:
      product_card: ".product-card"
      product_name: "[data-fixture-field='name']"
      price: "[data-fixture-field='price']"
      product_url: "[data-fixture-field='url']"
      image_url: ".product-card__hero-image"
    attributes:
      product_url: "href"
      image_url: "src"
""",
                encoding="utf-8",
            )

            with patch.dict("os.environ", {"APPROVED_HTML_LIST_URLS": "https://www.nike.com/kr/w/shoes"}, clear=False):
                with patch("backend.collectors.approved_html.requests.get") as get:
                    with self.assertRaises(ValueError):
                        ApprovedHtmlProductCollector(selector_config_path=config_path)

            get.assert_not_called()


if __name__ == "__main__":
    unittest.main()
