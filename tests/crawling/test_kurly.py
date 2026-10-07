import unittest

from crawler_engine.extractors.kurly import extract_kurly_candidates, product_id_from_url
from crawler_engine.models import CrawlRequest
from crawler_engine.sources import available_sources, select_sources


def _card(
    product_id="1001303421",
    name="14brix\uc774\uc0c1 \ubabb\uc0dd\uaca8\ub3c4 \ub9db\uc788\ub294 \uc0ac\uacfc 1.5kg",
    description="\uac70\uce5c \uc0dd\uae40\uc0c8 \uc18d \ub2ec\uace0 \ud48d\ubd80\ud55c \uacfc\uc999",
    original_price="24,900\uc6d0",
    sale_price="16,900\uc6d0",
    discount_rate="32%",
    image_url="https://product-image.kurly.com/product/image/abc/apple.jpg",
    extra="",
):
    return f"""
    <a class="product-card" href="/goods/{product_id}">
      <img class="collection-image" src="https://img-cf.kurly.com/filter.png" alt="\ud544\ud130">
      <img class="product-image" src="{image_url}" alt="{name}">
      <span class="delivery-label">\uc0db\ubcc4\ubc30\uc1a1</span>
      <span class="product-name">{name}</span>
      <p class="product-description">{description}</p>
      <span class="dimmed-price">{original_price}</span>
      <div class="discount-price">
        <span class="discount-rate">{discount_rate}</span>
        <span class="sales-price">{sale_price}</span>
      </div>
      <span class="review-count">999+</span>
      <span class="badge">Kurly Only</span>
      {extra}
    </a>
    """


class KurlySourceTest(unittest.TestCase):
    def test_kurly_source_url_and_metadata(self):
        source = available_sources()["kurly"]

        self.assertEqual(
            source.build_search_url(CrawlRequest(query="\uc0ac\uacfc")),
            "https://www.kurly.com/search?sword=%EC%82%AC%EA%B3%BC",
        )
        self.assertEqual(source.metadata.source, "kurly")
        self.assertEqual(source.metadata.default_condition, "new")
        self.assertTrue(source.metadata.require_positive_price)

    def test_kurly_runs_when_used_is_disabled(self):
        selected = select_sources(CrawlRequest(query="\uc0ac\uacfc", include_used=False), "kurly")

        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0].metadata.source, "kurly")


class KurlyExtractorTest(unittest.TestCase):
    def test_product_id_from_goods_url(self):
        self.assertEqual(product_id_from_url("/goods/1001303421"), "1001303421")
        self.assertEqual(product_id_from_url("https://www.kurly.com/goods/5061259?foo=bar"), "5061259")

    def test_extracts_product_name(self):
        candidate = extract_kurly_candidates(_card())[0]

        self.assertEqual(candidate.product_name, "14brix\uc774\uc0c1 \ubabb\uc0dd\uaca8\ub3c4 \ub9db\uc788\ub294 \uc0ac\uacfc 1.5kg")
        self.assertEqual(candidate.description, "\uac70\uce5c \uc0dd\uae40\uc0c8 \uc18d \ub2ec\uace0 \ud48d\ubd80\ud55c \uacfc\uc999")

    def test_sales_price_is_representative_price(self):
        candidate = extract_kurly_candidates(_card(original_price="24,900\uc6d0", sale_price="16,900\uc6d0"))[0]

        self.assertEqual(candidate.price, 16900)
        self.assertEqual(candidate.raw["original_price"], 24900)

    def test_dimmed_price_does_not_beat_sales_price(self):
        candidate = extract_kurly_candidates(_card(original_price="10,000\uc6d0", sale_price="16,900\uc6d0"))[0]

        self.assertEqual(candidate.price, 16900)

    def test_discount_rate_is_not_used_as_price(self):
        candidate = extract_kurly_candidates(_card(discount_rate="90%", sale_price="16,900\uc6d0"))[0]

        self.assertEqual(candidate.price, 16900)
        self.assertEqual(candidate.raw["discount_rate"], 90)

    def test_review_count_is_not_used_as_price(self):
        html = _card(sale_price="", extra='<span class="review-count">12,345</span>')

        self.assertEqual(extract_kurly_candidates(html), [])

    def test_extracts_representative_product_image(self):
        candidate = extract_kurly_candidates(_card(image_url="https://3p-image.kurly.com/product/apple.jpg"))[0]

        self.assertEqual(candidate.image_url, "https://3p-image.kurly.com/product/apple.jpg")

    def test_excludes_collection_and_sticker_images(self):
        html = _card(
            image_url="https://img-cf.kurly.com/product/apple.jpg",
            extra='<img class="sticker" src="https://img-cf.kurly.com/sticker.png" alt="\uc2a4\ud2f0\ucee4">',
        )
        candidate = extract_kurly_candidates(html)[0]

        self.assertEqual(candidate.image_url, "https://img-cf.kurly.com/product/apple.jpg")

    def test_relative_product_url_becomes_absolute(self):
        candidate = extract_kurly_candidates(_card())[0]

        self.assertEqual(candidate.product_url, "https://www.kurly.com/goods/1001303421")

    def test_duplicate_product_id_is_deduped(self):
        html = _card(product_id="1001303421", name="\uc0ac\uacfc A") + _card(product_id="1001303421", name="\uc0ac\uacfc B")

        candidates = extract_kurly_candidates(html)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].product_name, "\uc0ac\uacfc A")

    def test_missing_required_values_are_excluded(self):
        no_name = _card(name="")
        no_price = _card(sale_price="")
        no_image = _card(image_url="")

        self.assertEqual(extract_kurly_candidates(no_name + no_price + no_image), [])

    def test_extracts_multiple_normal_cards(self):
        html = (
            _card(product_id="1001303421", name="\uc0ac\uacfc A", sale_price="16,900\uc6d0")
            + _card(product_id="5061259", name="\uc0ac\uacfc B", sale_price="9,900\uc6d0")
            + _card(product_id="1234567", name="\uc0ac\uacfc C", sale_price="12,900\uc6d0")
        )

        candidates = extract_kurly_candidates(html)

        self.assertEqual(len(candidates), 3)
        self.assertEqual([candidate.raw["product_id"] for candidate in candidates], ["1001303421", "5061259", "1234567"])
        self.assertEqual([candidate.price for candidate in candidates], [16900, 9900, 12900])
        self.assertTrue(all(candidate.source == "kurly" for candidate in candidates))
        self.assertTrue(all(candidate.condition == "new" for candidate in candidates))
        self.assertTrue(all(candidate.currency == "KRW" for candidate in candidates))


if __name__ == "__main__":
    unittest.main()
