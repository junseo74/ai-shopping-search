import unittest

from crawler_engine.extractors.lotteon import extract_lotteon_candidates, product_id_from_url, sitm_no_from_url
from crawler_engine.models import CrawlRequest
from crawler_engine.sources import available_sources, select_sources


def _card(
    product_id="LO2427231679",
    sitm_no="LO2427231679_2427231688",
    name="KT\uae30\uae30\ubcc0\uacbd \uac24\ub7ed\uc2dcS25 \uc5e3\uc9c0 256GB \uae30\uc900\uc694\uae08\uc81c 30 \uacf5\ud1b5\uc9c0\uc6d0",
    image_url="https://contents.lotteon.com/itemimage/LO/24/27/23/16/79/LO2427231679_1.jpg",
    real_price="440,900",
    sale="2%",
    final_price="429,990",
    extra="",
    title_class="c-product-title",
):
    price_html = f"""
      <div class="c-product-price">
        <span class="c-product-price__real">{real_price} \uc815\uc0c1\uac00</span>
        <span class="c-product-price__sale">{sale} \ud560\uc778\uc728</span>
        <span class="c-product-price__final">{final_price} \ucd5c\uc885\uac00</span>
      </div>
    """
    return f"""
    <li class="c-product-list__item">
      <div class="c-product-card">
        <a class="c-product-card__link" href="/p/product/{product_id}?sitmNo={sitm_no}&mall_no=1">
          <img src="{image_url}" alt="{name}">
        </a>
        <div class="{title_class}">{name}</div>
        {price_html}
        <div class="c-product-review">5.0 \uace0\uac1d\ud3c9\uc810 3 \ub9ac\ubdf0</div>
        {extra}
      </div>
    </li>
    """


def _single_price_card(product_id="LO100", price="44,900", name="\uac24\ub7ed\uc2dc S25 \ucf00\uc774\uc2a4"):
    return f"""
    <li class="c-product-list__item">
      <div class="c-product-card">
        <a href="https://www.lotteon.com/p/product/{product_id}?sitmNo={product_id}_1">
          <img src="https://contents.lotteon.com/itemimage/{product_id}.jpg" alt="{name}">
        </a>
        <div class="c-product-title">{name}</div>
        <div class="c-product-price">
          <span class="c-product-price__final">{price} \ucd5c\uc885\uac00</span>
        </div>
      </div>
    </li>
    """


class LotteOnSourceTest(unittest.TestCase):
    def test_source_url_and_metadata(self):
        source = available_sources()["lotteon"]

        self.assertEqual(
            source.build_search_url(CrawlRequest(query="\uac24\ub7ed\uc2dc S25")),
            "https://www.lotteon.com/csearch/search/search?render=search&platform=pc&q=%EA%B0%A4%EB%9F%AD%EC%8B%9C%20S25&sort=ranking",
        )
        self.assertEqual(source.metadata.source, "lotteon")
        self.assertEqual(source.metadata.display_name, "LotteON")
        self.assertEqual(source.metadata.default_condition, "new")
        self.assertTrue(source.metadata.require_positive_price)

    def test_source_runs_when_used_is_disabled(self):
        selected = select_sources(CrawlRequest(query="\uac24\ub7ed\uc2dc S25", include_used=False), "lotteon")

        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0].metadata.source, "lotteon")


class LotteOnExtractorTest(unittest.TestCase):
    def test_product_id_and_sitm_no_from_url(self):
        url = "https://www.lotteon.com/p/product/LO2427231679?sitmNo=LO2427231679_2427231688"

        self.assertEqual(product_id_from_url(url), "LO2427231679")
        self.assertEqual(sitm_no_from_url(url), "LO2427231679_2427231688")

    def test_extracts_normal_product_card(self):
        candidate = extract_lotteon_candidates(_card())[0]

        self.assertEqual(candidate.raw["product_id"], "LO2427231679")
        self.assertEqual(candidate.raw["sitm_no"], "LO2427231679_2427231688")
        self.assertIn("\uac24\ub7ed\uc2dcS25", candidate.product_name)
        self.assertEqual(candidate.price, 429990)
        self.assertEqual(candidate.raw["original_price"], 440900)
        self.assertEqual(candidate.raw["discount_rate"], 2)
        self.assertEqual(candidate.raw["rating"], 5.0)
        self.assertEqual(candidate.raw["review_count"], 3)
        self.assertEqual(candidate.product_url, "https://www.lotteon.com/p/product/LO2427231679")
        self.assertEqual(candidate.image_url, "https://contents.lotteon.com/itemimage/LO/24/27/23/16/79/LO2427231679_1.jpg")
        self.assertEqual(candidate.source, "lotteon")
        self.assertEqual(candidate.condition, "new")
        self.assertEqual(candidate.currency, "KRW")

    def test_uses_final_price_for_discounted_product(self):
        candidate = extract_lotteon_candidates(_card(real_price="440,900", sale="2%", final_price="429,990"))[0]

        self.assertEqual(candidate.price, 429990)
        self.assertEqual(candidate.raw["original_price"], 440900)
        self.assertEqual(candidate.raw["discount_rate"], 2)

    def test_uses_final_price_without_discount(self):
        candidate = extract_lotteon_candidates(_single_price_card(price="44,900"))[0]

        self.assertEqual(candidate.price, 44900)
        self.assertIsNone(candidate.raw["original_price"])
        self.assertIsNone(candidate.raw["discount_rate"])

    def test_accepts_one_hundred_won_display_price(self):
        candidate = extract_lotteon_candidates(_single_price_card(product_id="LO200", price="100"))[0]

        self.assertEqual(candidate.price, 100)

    def test_missing_product_id_or_product_url_is_excluded(self):
        html = """
        <li class="c-product-list__item">
          <div class="c-product-card">
            <img src="https://contents.lotteon.com/itemimage/no-url.jpg" alt="\uc0c1\ud488">
            <div class="c-product-title">\uc0c1\ud488</div>
            <div class="c-product-price"><span class="c-product-price__final">10,000 \ucd5c\uc885\uac00</span></div>
          </div>
        </li>
        """

        self.assertEqual(extract_lotteon_candidates(html), [])

    def test_card_data_does_not_mix_between_cards(self):
        html = (
            _card(product_id="LO1", sitm_no="LO1_1", name="\uc0c1\ud488 A", final_price="10,000")
            + _card(product_id="LO2", sitm_no="LO2_1", name="\uc0c1\ud488 B", final_price="20,000")
        )

        candidates = extract_lotteon_candidates(html)

        self.assertEqual([candidate.raw["product_id"] for candidate in candidates], ["LO1", "LO2"])
        self.assertEqual([candidate.product_name for candidate in candidates], ["\uc0c1\ud488 A", "\uc0c1\ud488 B"])
        self.assertEqual([candidate.price for candidate in candidates], [10000, 20000])

    def test_duplicate_product_id_is_deduped(self):
        candidates = extract_lotteon_candidates(
            _card(product_id="LO1", sitm_no="LO1_1", name="\uc0c1\ud488 A")
            + _card(product_id="LO1", sitm_no="LO1_2", name="\uc0c1\ud488 B")
        )

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].product_name, "\uc0c1\ud488 A")

    def test_malformed_cards_do_not_crash(self):
        html = """
        <li class="c-product-list__item">
          <div class="c-product-card">
            <a href="/p/product/LO404"></a>
            <div class="c-product-title"></div>
          </div>
        </li>
        """

        self.assertEqual(extract_lotteon_candidates(html), [])


if __name__ == "__main__":
    unittest.main()
