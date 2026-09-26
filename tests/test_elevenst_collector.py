import os
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch

from backend.collectors import ElevenstProductCollector


class ElevenstProductCollectorTest(unittest.TestCase):
    def test_missing_credentials_does_not_return_fake_products(self):
        with patch.dict(os.environ, {"ELEVENST_API_KEY": ""}, clear=False):
            collector = ElevenstProductCollector()
            with self.assertRaises(RuntimeError):
                collector.collect(query="coffee", limit=1)

    def test_maps_product_search_xml_to_product(self):
        xml = """
        <Product>
          <ProductCode>123</ProductCode>
          <ProductName>Example Korean Coffee</ProductName>
          <ProductPrice>12900</ProductPrice>
          <ProductImage>http://image.11st.co.kr/example.jpg</ProductImage>
          <Seller>example-seller</Seller>
          <DetailPageUrl>http://www.11st.co.kr/product/SellerProductDetail.tmall?prdNo=123</DetailPageUrl>
          <Delivery>무료</Delivery>
        </Product>
        """
        collector = ElevenstProductCollector()
        product = collector._product_from_xml(ET.fromstring(xml))

        self.assertEqual(product.product_name, "Example Korean Coffee")
        self.assertEqual(product.price, 12900.0)
        self.assertEqual(product.shipping_fee, 0.0)
        self.assertEqual(product.seller, "example-seller")
        self.assertEqual(str(product.product_url), "http://www.11st.co.kr/product/SellerProductDetail.tmall?prdNo=123")
        self.assertEqual(product.data_source, "elevenst")


if __name__ == "__main__":
    unittest.main()
