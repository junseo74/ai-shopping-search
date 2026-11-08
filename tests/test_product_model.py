import unittest

from backend.models import PlatformType, Product, ProductCondition


class ProductModelTest(unittest.TestCase):
    def test_food_fields_are_optional(self):
        product = Product(
            product_name="Apple juice",
            platform=PlatformType.SHOPPING_MALL,
            condition=ProductCondition.NEW,
            data_source="fixture",
        )

        self.assertIsNone(product.ingredients)
        self.assertIsNone(product.allergens)

    def test_food_fields_can_be_populated(self):
        product = Product(
            product_name="Apple juice",
            platform=PlatformType.SHOPPING_MALL,
            condition=ProductCondition.NEW,
            data_source="fixture",
            ingredients="Apple concentrate 99%, vitamin C",
            allergens=["soy", "peach"],
        )

        self.assertEqual(product.ingredients, "Apple concentrate 99%, vitamin C")
        self.assertEqual(product.allergens, ["soy", "peach"])


if __name__ == "__main__":
    unittest.main()
