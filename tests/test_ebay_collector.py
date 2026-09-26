import os
import unittest
from unittest.mock import patch

from backend.collectors import EbayBrowseCollector
from backend.models import ProductCondition


class EbayBrowseCollectorTest(unittest.TestCase):
    def test_missing_credentials_does_not_return_fake_products(self):
        with patch.dict(os.environ, {"EBAY_CLIENT_ID": "", "EBAY_CLIENT_SECRET": ""}, clear=False):
            collector = EbayBrowseCollector()
            with self.assertRaises(RuntimeError):
                collector.collect(query="phone", limit=1)

    def test_maps_item_summary_to_product(self):
        collector = EbayBrowseCollector()
        product = collector._to_product(
            {
                "title": "Example Phone",
                "price": {"value": "199.99", "currency": "USD"},
                "shippingOptions": [{"shippingCost": {"value": "5.00", "currency": "USD"}}],
                "seller": {"username": "example-seller"},
                "itemWebUrl": "https://www.ebay.com/itm/123",
                "image": {"imageUrl": "https://i.ebayimg.com/images/example.jpg"},
                "condition": "Used",
                "categories": [{"categoryName": "Cell Phones"}],
                "itemLocation": {"city": "San Jose", "country": "US"},
            }
        )

        self.assertEqual(product.product_name, "Example Phone")
        self.assertEqual(product.price, 199.99)
        self.assertEqual(product.shipping_fee, 5.0)
        self.assertEqual(product.seller, "example-seller")
        self.assertEqual(product.condition, ProductCondition.USED)
        self.assertEqual(product.data_source, "ebay_browse")


if __name__ == "__main__":
    unittest.main()
