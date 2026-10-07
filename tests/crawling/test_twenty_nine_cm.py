import unittest

from crawler_engine.extractors.twenty_nine_cm import extract_twenty_nine_cm_candidates, product_id_from_url
from crawler_engine.models import CrawlRequest
from crawler_engine.sources import available_sources, select_sources


def _card(
    product_id="4247448",
    brand="\ub098\uc774\ud0a4",
    name="\ubb38 \uc288 W - [\ubbf8\uc2a4\ud2f1 \ub370\uc774\uce20:\ud130\ud504 \ub808\ub4dc:\uac80 \ub77c\uc774\ud2b8 \ube0c\ub77c\uc6b4:\uc138\uc77c / IX7025-600]",
    price="139,000",
    discount="",
    image_url="https://img.29cm.co.kr/item/202601/4247448.jpg",
    extra="",
):
    return f"""
    <li>
      <div class="mb-40 space-y-12">
        <a href="https://product.29cm.co.kr/catalog/{product_id}?search_keyword=%EB%82%98%EC%9D%B4%ED%82%A4">
          <img src="{image_url}" alt="{name}">
        </a>
        <div class="brand">{brand}</div>
        <div class="name">{name}</div>
        <div class="price">{discount} {price}</div>
        <div class="review">5 리뷰 999 좋아요 123</div>
        {extra}
      </div>
    </li>
    """


class TwentyNineCmSourceTest(unittest.TestCase):
    def test_source_url_and_metadata(self):
        source = available_sources()["29cm"]

        self.assertEqual(
            source.build_search_url(CrawlRequest(query="\ub098\uc774\ud0a4")),
            "https://www.29cm.co.kr/store/search?keyword=%EB%82%98%EC%9D%B4%ED%82%A4&sort=RECOMMENDED&page=1",
        )
        self.assertEqual(source.metadata.source, "29cm")
        self.assertEqual(source.metadata.display_name, "29CM")
        self.assertEqual(source.metadata.default_condition, "new")
        self.assertTrue(source.metadata.require_positive_price)

    def test_source_runs_when_used_is_disabled(self):
        selected = select_sources(CrawlRequest(query="\ub098\uc774\ud0a4", include_used=False), "29cm")

        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0].metadata.source, "29cm")


class TwentyNineCmExtractorTest(unittest.TestCase):
    def test_product_id_from_catalog_url(self):
        self.assertEqual(
            product_id_from_url("https://product.29cm.co.kr/catalog/4247448?search_keyword=x"),
            "4247448",
        )
        self.assertEqual(product_id_from_url("/catalog/1234567"), "1234567")

    def test_extracts_product_name(self):
        candidate = extract_twenty_nine_cm_candidates(_card())[0]

        self.assertIn("IX7025-600", candidate.product_name)

    def test_img_alt_is_name_fallback(self):
        html = """
        <li><div>
          <a href="https://product.29cm.co.kr/catalog/4247448">
            <img src="https://img.29cm.co.kr/item/202601/4247448.jpg" alt="\uc5d0\uc5b4 \ud3ec\uc2a4 1 07">
          </a>
          <div>\ub098\uc774\ud0a4</div><div>152,100</div>
        </div></li>
        """

        candidate = extract_twenty_nine_cm_candidates(html)[0]

        self.assertEqual(candidate.product_name, "\uc5d0\uc5b4 \ud3ec\uc2a4 1 07")

    def test_normal_price_extracts_grouped_number(self):
        candidate = extract_twenty_nine_cm_candidates(_card(price="139,000"))[0]

        self.assertEqual(candidate.price, 139000)

    def test_ten_percent_discount_is_not_price(self):
        candidate = extract_twenty_nine_cm_candidates(_card(discount="10%", price="152,100"))[0]

        self.assertEqual(candidate.price, 152100)
        self.assertEqual(candidate.raw["discount_rate"], 10)

    def test_thirty_percent_discount_is_not_price(self):
        candidate = extract_twenty_nine_cm_candidates(_card(discount="30%", price="132,300"))[0]

        self.assertEqual(candidate.price, 132300)
        self.assertEqual(candidate.raw["discount_rate"], 30)

    def test_review_and_rating_numbers_are_not_price(self):
        html = _card(price="", extra="<div>평점 5 리뷰 999 좋아요 123</div>")

        self.assertEqual(extract_twenty_nine_cm_candidates(html), [])

    def test_extracts_item_image(self):
        candidate = extract_twenty_nine_cm_candidates(_card(image_url="https://img.29cm.co.kr/item/sample.jpg"))[0]

        self.assertEqual(candidate.image_url, "https://img.29cm.co.kr/item/sample.jpg")

    def test_excludes_cms_logo_banner_images(self):
        html = """
        <li><div>
          <a href="https://product.29cm.co.kr/catalog/4247448">
            <img src="https://img.29cm.co.kr/cms/banner.jpg" alt="banner">
            <img src="https://img.29cm.co.kr/item/202601/4247448.jpg" alt="\uc0c1\ud488">
          </a>
          <div>\ub098\uc774\ud0a4</div><div>139,000</div>
        </div></li>
        """

        candidate = extract_twenty_nine_cm_candidates(html)[0]

        self.assertEqual(candidate.image_url, "https://img.29cm.co.kr/item/202601/4247448.jpg")

    def test_product_url_is_canonicalized(self):
        candidate = extract_twenty_nine_cm_candidates(_card())[0]

        self.assertEqual(candidate.product_url, "https://product.29cm.co.kr/catalog/4247448")

    def test_duplicate_product_id_is_deduped(self):
        candidates = extract_twenty_nine_cm_candidates(
            _card(product_id="4247448", name="\uc0c1\ud488 A") + _card(product_id="4247448", name="\uc0c1\ud488 B")
        )

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].product_name, "\uc0c1\ud488 A")

    def test_missing_required_values_are_excluded(self):
        no_name = _card(name="", image_url="https://img.29cm.co.kr/item/no-name.jpg")
        no_price = _card(product_id="2", price="")
        no_image = _card(product_id="3", image_url="https://img.29cm.co.kr/cms/banner.jpg")

        self.assertEqual(extract_twenty_nine_cm_candidates(no_name + no_price + no_image), [])

    def test_extracts_multiple_normal_cards(self):
        html = (
            _card(product_id="4247448", name="\uc0c1\ud488 A", price="139,000")
            + _card(product_id="4247449", name="\uc0c1\ud488 B", discount="10%", price="152,100")
            + _card(product_id="4247450", name="\uc0c1\ud488 C", discount="30%", price="132,300")
        )

        candidates = extract_twenty_nine_cm_candidates(html)

        self.assertEqual(len(candidates), 3)
        self.assertEqual([candidate.raw["product_id"] for candidate in candidates], ["4247448", "4247449", "4247450"])
        self.assertEqual([candidate.price for candidate in candidates], [139000, 152100, 132300])
        self.assertTrue(all(candidate.source == "29cm" for candidate in candidates))
        self.assertTrue(all(candidate.condition == "new" for candidate in candidates))
        self.assertTrue(all(candidate.currency == "KRW" for candidate in candidates))


if __name__ == "__main__":
    unittest.main()
