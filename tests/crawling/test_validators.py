import unittest

from crawler_engine.models import CrawledProduct
from crawler_engine.normalize import normalize_price
from crawler_engine.validators import dedupe_products


class ValidatorsTest(unittest.TestCase):
    def test_price_normalization_for_danawa_format(self):
        self.assertEqual(normalize_price("1,077,870\uc6d0"), 1077870)

    def test_dedupe_products(self):
        first = CrawledProduct(
            product_name="\uc0bc\uc131\uc804\uc790 \uac24\ub7ed\uc2dcS25",
            price=1077870,
            currency="KRW",
            source="danawa",
            seller=None,
            condition="new",
            country="KR",
            product_url="https://prod.danawa.com/info/?pcode=102124202",
            image_url=None,
            description=None,
        )
        second = CrawledProduct(
            product_name="\uc0bc\uc131\uc804\uc790 \uac24\ub7ed\uc2dcS25",
            price=1077870,
            currency="KRW",
            source="danawa",
            seller=None,
            condition="new",
            country="KR",
            product_url="https://prod.danawa.com/info/?pcode=102124202",
            image_url=None,
            description=None,
        )

        self.assertEqual(dedupe_products([first, second]), [first])


if __name__ == "__main__":
    unittest.main()
