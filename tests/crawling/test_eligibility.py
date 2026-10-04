import unittest

from crawler_engine.aggregation import aggregate_candidates
from crawler_engine.eligibility import is_eligible_product_candidate
from crawler_engine.extractors import extract_dom_candidates
from crawler_engine.models import ProductCandidate
from crawler_engine.sites.danawa import DanawaSource


class EligibilityTest(unittest.TestCase):
    def test_canonical_danawa_product_url_is_allowed(self):
        candidate = ProductCandidate(
            product_name="\uc0bc\uc131\uc804\uc790 \uac24\ub7ed\uc2dc S25 256GB \uc790\uae09\uc81c",
            price=1077870,
            product_url="https://prod.danawa.com/info/?pcode=102124202",
        )

        self.assertTrue(is_eligible_product_candidate(candidate, DanawaSource.metadata, "https://search.danawa.com"))

    def test_dpg_news_and_bbs_urls_are_excluded(self):
        for url in (
            "https://dpg.danawa.com/news/view?boardSeq=60&listSeq=1",
            "https://dpg.danawa.com/bbs/view?boardSeq=28&listSeq=1",
        ):
            candidate = ProductCandidate(
                product_name="\uc0bc\uc131\uc804\uc790 \uac24\ub7ed\uc2dc S25",
                price=1000,
                product_url=url,
            )

            self.assertFalse(is_eligible_product_candidate(candidate, DanawaSource.metadata, "https://search.danawa.com"))

    def test_ad_redirect_url_is_excluded_by_default(self):
        candidate = ProductCandidate(
            product_name="\uc0bc\uc131\uc804\uc790 \uac24\ub7ed\uc2dc S25",
            price=1000,
            product_url="https://ad.danawa.com/bridge?url=https%3A%2F%2Fprod.danawa.com%2Finfo%2F%3Fpcode%3D1",
        )

        self.assertFalse(is_eligible_product_candidate(candidate, DanawaSource.metadata, "https://search.danawa.com"))

    def test_zero_price_danawa_candidate_is_excluded(self):
        candidate = ProductCandidate(
            product_name="\uc0bc\uc131\uc804\uc790 \uac24\ub7ed\uc2dc S25",
            price=0,
            product_url="https://prod.danawa.com/info/?pcode=102124202",
        )

        self.assertFalse(is_eligible_product_candidate(candidate, DanawaSource.metadata, "https://search.danawa.com"))

    def test_ui_phrase_only_name_is_excluded(self):
        candidate = ProductCandidate(
            product_name="\uc694\uae08\ud560\uc778(\uc120\ud0dd\uc57d\uc815)",
            price=1000,
            product_url="https://prod.danawa.com/info/?pcode=102124202",
        )

        self.assertFalse(is_eligible_product_candidate(candidate, DanawaSource.metadata, "https://search.danawa.com"))

    def test_canonical_product_is_kept_after_aggregation(self):
        aggregated = aggregate_candidates(
            [
                ProductCandidate(
                    product_name="\uc0bc\uc131\uc804\uc790 \uac24\ub7ed\uc2dc S25 256GB \uc790\uae09\uc81c",
                    price_text="1,077,870\uc6d0",
                    product_url="https://prod.danawa.com/info/?pcode=102124202",
                )
            ],
            DanawaSource.metadata,
            "https://search.danawa.com/dsearch.php",
        )

        self.assertTrue(is_eligible_product_candidate(aggregated[0], DanawaSource.metadata, "https://search.danawa.com"))

    def test_srcset_and_data_srcset_images_are_extracted(self):
        html = """
        <ul>
          <li>
            <a href="https://prod.danawa.com/info/?pcode=1">
              <img srcset="https://img.danawa.com/one.jpg 1x, https://img.danawa.com/two.jpg 2x" alt="\uc0bc\uc131 \uac24\ub7ed\uc2dcS25" />
            </a>
            <span>1,077,870\uc6d0</span>
          </li>
          <li>
            <a href="https://prod.danawa.com/info/?pcode=2">
              <img data-srcset="/lazy-one.jpg 1x, /lazy-two.jpg 2x" alt="\uc0bc\uc131 \uac24\ub7ed\uc2dcS25 \ud50c\ub7ec\uc2a4" />
            </a>
            <span>1,177,870\uc6d0</span>
          </li>
        </ul>
        """

        candidates = extract_dom_candidates(html, product_url_hints=DanawaSource.metadata.product_url_hints)

        self.assertEqual(candidates[0].image_url, "https://img.danawa.com/one.jpg")
        self.assertEqual(candidates[1].image_url, "/lazy-one.jpg")

    def test_aggregation_keeps_group_image(self):
        aggregated = aggregate_candidates(
            [
                ProductCandidate(
                    product_name="\uc0bc\uc131\uc804\uc790 \uac24\ub7ed\uc2dc S25 256GB \uc790\uae09\uc81c",
                    price_text="1,077,870\uc6d0",
                    product_url="https://prod.danawa.com/info/?pcode=102124202",
                ),
                ProductCandidate(
                    product_name="\uc0bc\uc131\uc804\uc790 \uac24\ub7ed\uc2dc S25",
                    price_text="1,077,870\uc6d0",
                    product_url="https://prod.danawa.com/info/?pcode=102124202",
                    image_url="https://img.danawa.com/prod.jpg",
                ),
            ],
            DanawaSource.metadata,
            "https://search.danawa.com/dsearch.php",
        )

        self.assertEqual(aggregated[0].image_url, "https://img.danawa.com/prod.jpg")

    def test_card_image_associates_with_sibling_canonical_link(self):
        html = """
        <li>
          <div><img src="https://img.danawa.com/prod.jpg" alt="\uc0bc\uc131\uc804\uc790 \uac24\ub7ed\uc2dcS25 256GB" /></div>
          <p><a href="https://prod.danawa.com/info/?pcode=102124202">\uc0bc\uc131\uc804\uc790 \uac24\ub7ed\uc2dcS25 256GB \uc790\uae09\uc81c</a></p>
          <span>1,077,870\uc6d0</span>
        </li>
        """

        candidates = extract_dom_candidates(html, product_url_hints=DanawaSource.metadata.product_url_hints)
        aggregated = aggregate_candidates(candidates, DanawaSource.metadata, "https://search.danawa.com/dsearch.php")

        self.assertEqual(len(aggregated), 1)
        self.assertEqual(aggregated[0].product_url, "https://prod.danawa.com/info/?pcode=102124202")
        self.assertEqual(aggregated[0].image_url, "https://img.danawa.com/prod.jpg")

    def test_images_do_not_cross_product_cards(self):
        html = """
        <ul>
          <li>
            <img src="https://img.danawa.com/one.jpg" alt="\uc0bc\uc131 \uac24\ub7ed\uc2dcS25" />
            <a href="https://prod.danawa.com/info/?pcode=1">\uc0bc\uc131 \uac24\ub7ed\uc2dcS25</a>
            <span>1,077,870\uc6d0</span>
          </li>
          <li>
            <img src="https://img.danawa.com/two.jpg" alt="\uc0bc\uc131 \uac24\ub7ed\uc2dcS25 \ud50c\ub7ec\uc2a4" />
            <a href="https://prod.danawa.com/info/?pcode=2">\uc0bc\uc131 \uac24\ub7ed\uc2dcS25 \ud50c\ub7ec\uc2a4</a>
            <span>1,177,870\uc6d0</span>
          </li>
        </ul>
        """

        candidates = extract_dom_candidates(html, product_url_hints=DanawaSource.metadata.product_url_hints)
        aggregated = aggregate_candidates(candidates, DanawaSource.metadata, "https://search.danawa.com/dsearch.php")
        images = {candidate.product_url: candidate.image_url for candidate in aggregated}

        self.assertEqual(images["https://prod.danawa.com/info/?pcode=1"], "https://img.danawa.com/one.jpg")
        self.assertEqual(images["https://prod.danawa.com/info/?pcode=2"], "https://img.danawa.com/two.jpg")

    def test_placeholder_data_image_exclusion_still_applies(self):
        html = """
        <li>
          <img src="data:image/gif;base64,AAAA" alt="\uc0bc\uc131 \uac24\ub7ed\uc2dcS25" />
          <a href="https://prod.danawa.com/info/?pcode=1">\uc0bc\uc131 \uac24\ub7ed\uc2dcS25</a>
          <span>1,077,870\uc6d0</span>
        </li>
        """

        candidates = extract_dom_candidates(html, product_url_hints=DanawaSource.metadata.product_url_hints)
        aggregated = aggregate_candidates(candidates, DanawaSource.metadata, "https://search.danawa.com/dsearch.php")

        self.assertIsNone(aggregated[0].image_url)

    def test_danawa_product_item_card_maps_canonical_fields_and_image(self):
        html = """
        <ul>
          <li id="productItem102126383" class="prod_item" data-product-order="4">
            <div class="prod_main_info">
              <div class="thumb_image">
                <a href="https://prod.danawa.com/info/?pcode=102126383&amp;keyword=x&amp;cate=122515">
                  <img src="https://img.danuri.io/catalog-image/383/126/102/product.jpg"
                       alt="\uac24\ub7ed\uc2dcS25 \uc6b8\ud2b8\ub77c 256GB, \uc790\uae09\uc81c">
                </a>
              </div>
              <div class="prod_info">
                <p class="prod_name">
                  <a href="https://prod.danawa.com/info/?pcode=102126383&amp;keyword=x&amp;cate=122515">
                    \uc0bc\uc131\uc804\uc790 <b>\uac24\ub7ed\uc2dc</b><b>S25</b> \uc6b8\ud2b8\ub77c 256GB, \uc790\uae09\uc81c
                  </a>
                </p>
                <div class="spec_list">
                  <a href="#">\ucd9c\uc2dc\uac00: 1,698,400\uc6d0</a>
                </div>
              </div>
              <div class="prod_pricelist">
                <ul>
                  <li id="productInfoDetail_102126383">
                    <a href="https://prod.danawa.com/info/?pcode=102126383&amp;keyword=x&amp;cate=122515">
                      <strong>1,473,100</strong>\uc6d0
                    </a>
                  </li>
                </ul>
              </div>
            </div>
          </li>
        </ul>
        """

        candidates = extract_dom_candidates(
            html,
            product_url_hints=DanawaSource.metadata.product_url_hints,
            query="\uac24\ub7ed\uc2dc S25",
        )
        aggregated = aggregate_candidates(
            candidates,
            DanawaSource.metadata,
            "https://search.danawa.com/dsearch.php",
            query="\uac24\ub7ed\uc2dc S25",
        )

        self.assertEqual(len(aggregated), 1)
        self.assertEqual(aggregated[0].product_url, "https://prod.danawa.com/info/?pcode=102126383")
        self.assertEqual(aggregated[0].product_name, "\uc0bc\uc131\uc804\uc790 \uac24\ub7ed\uc2dc S25 \uc6b8\ud2b8\ub77c 256GB, \uc790\uae09\uc81c")
        self.assertEqual(aggregated[0].price, 1473100)
        self.assertEqual(aggregated[0].image_url, "https://img.danuri.io/catalog-image/383/126/102/product.jpg")

    def test_danawa_lazy_placeholder_image_uses_data_src(self):
        html = """
        <li id="productItem75001853" class="prod_item">
          <a href="https://prod.danawa.com/info/?pcode=75001853">
            <img src="//img.danawa.com/new/noData/img/noImg_160.gif"
                 data-src="https://img.danuri.io/catalog-image/853/001/075/product.jpg"
                 alt="\uac24\ub7ed\uc2dcS25 256GB, \uc790\uae09\uc81c">
          </a>
          <a href="https://prod.danawa.com/info/?pcode=75001853">
            \uc0bc\uc131\uc804\uc790 \uac24\ub7ed\uc2dcS25 256GB, \uc790\uae09\uc81c
          </a>
          <a href="https://prod.danawa.com/info/?pcode=75001853">
            <strong>1,225,990</strong>\uc6d0
          </a>
        </li>
        """

        candidates = extract_dom_candidates(html, product_url_hints=DanawaSource.metadata.product_url_hints)
        aggregated = aggregate_candidates(candidates, DanawaSource.metadata, "https://search.danawa.com/dsearch.php")

        self.assertEqual(aggregated[0].image_url, "https://img.danuri.io/catalog-image/853/001/075/product.jpg")


if __name__ == "__main__":
    unittest.main()
