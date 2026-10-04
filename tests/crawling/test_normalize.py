import unittest

from crawler_engine.models import ProductCandidate, SourceMetadata
from crawler_engine.normalize import normalize_candidate, normalize_price, normalize_url


class NormalizeTest(unittest.TestCase):
    def test_price_text_to_integer(self):
        self.assertEqual(normalize_price("650,000\uc6d0"), 650000)
        self.assertEqual(normalize_price("650000\uc6d0"), 650000)
        self.assertEqual(normalize_price("\uc544\uc774\ud3f0 15 128GB 650,000\uc6d0"), 650000)
        self.assertEqual(normalize_price("\uac24\ub7ed\uc2dc S25 256GB 1,077,870\uc6d0"), 1077870)
        self.assertIsNone(normalize_price("\ubb34\ub8cc\ub098\ub214"))
        self.assertIsNone(normalize_price("\uac00\uaca9\uc81c\uc548"))
        self.assertIsNone(normalize_price("\uc544\uc774\ud3f0 15 128GB 650000"))

    def test_structured_price_values(self):
        self.assertEqual(normalize_price("650000", structured=True), 650000)
        self.assertEqual(normalize_price(650000, structured=True), 650000)
        self.assertEqual(normalize_price("1,077,870", structured=True), 1077870)
        self.assertIsNone(normalize_price("\uc544\uc774\ud3f0 15 128GB 650000", structured=True))

    def test_relative_url_to_absolute(self):
        self.assertEqual(
            normalize_url("/product/123", "https://web.joongna.com/search/iphone"),
            "https://web.joongna.com/product/123",
        )

    def test_candidate_normalization_is_independent_from_backend(self):
        product = normalize_candidate(
            ProductCandidate(
                product_name="\uc544\uc774\ud3f0 15 128GB",
                price_text="650,000\uc6d0",
                seller="\ud310\ub9e4\uc790",
                product_url="/product/123",
                image_url="/image.jpg",
            ),
            SourceMetadata(source="joongna", display_name="Joonggonara", used_only=True),
            "https://web.joongna.com/search/\uc544\uc774\ud3f0",
        )

        self.assertIsNotNone(product)
        self.assertEqual(product.price, 650000)
        self.assertEqual(product.condition, "used")
        self.assertEqual(product.source, "joongna")

    def test_default_condition_from_source_metadata(self):
        joongna = normalize_candidate(
            ProductCandidate(product_name="\uc544\uc774\ud3f0", price_text="650,000\uc6d0"),
            SourceMetadata(source="joongna", display_name="Joonggonara", used_only=True),
            "https://web.joongna.com/search/\uc544\uc774\ud3f0",
        )
        danawa = normalize_candidate(
            ProductCandidate(product_name="\uac24\ub7ed\uc2dc S25", price_text="1,077,870\uc6d0"),
            SourceMetadata(source="danawa", display_name="Danawa", default_condition="new"),
            "https://search.danawa.com/dsearch.php?query=s25",
        )
        explicit = normalize_candidate(
            ProductCandidate(product_name="\ub9ac\ud37c", price_text="100,000\uc6d0", condition="refurbished"),
            SourceMetadata(source="example", display_name="Example", default_condition="new"),
            "https://example.com",
        )

        self.assertEqual(joongna.condition, "used")
        self.assertEqual(danawa.condition, "new")
        self.assertEqual(explicit.condition, "refurbished")


if __name__ == "__main__":
    unittest.main()
