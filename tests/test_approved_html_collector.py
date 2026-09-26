import unittest

from backend.collectors import HtmlProductParser


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


if __name__ == "__main__":
    unittest.main()
