import unittest

from crawler_engine.extractors import (
    extract_dom_candidates,
    extract_embedded_data_candidates,
    extract_json_ld_candidates,
)
from crawler_engine.models import SourceMetadata
from crawler_engine.normalize import normalize_candidate


class ExtractorsTest(unittest.TestCase):
    def test_json_ld_product(self):
        html = """
        <script type="application/ld+json">
        {
          "@type": "Product",
          "name": "\uc544\uc774\ud3f0 15",
          "image": "https://example.com/a.jpg",
          "description": "\uc0c1\ud0dc \uc88b\uc74c",
          "offers": {"price": "650000", "priceCurrency": "KRW", "url": "/product/1"}
        }
        </script>
        """

        candidates = extract_json_ld_candidates(html)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].product_name, "\uc544\uc774\ud3f0 15")
        self.assertEqual(candidates[0].price, 650000)

    def test_json_ld_numeric_price_product(self):
        html = """
        <script type="application/ld+json">
        {
          "@type": "Product",
          "name": "\uc544\uc774\ud3f0 15",
          "offers": {"price": 650000, "priceCurrency": "KRW", "url": "/product/1"}
        }
        </script>
        """

        candidates = extract_json_ld_candidates(html)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].price, 650000)

    def test_embedded_data_candidate(self):
        html = """
        <script id="__NEXT_DATA__" type="application/json">
        {"props":{"items":[{"productName":"\uc544\uc774\ud3f0 15","price":"650,000\uc6d0","productUrl":"/product/1"}]}}
        </script>
        """

        candidates = extract_embedded_data_candidates(html)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].product_name, "\uc544\uc774\ud3f0 15")

    def test_dom_link_block_candidate(self):
        html = """
        <a href="/product/1">
          <img src="/a.jpg" alt="\uc544\uc774\ud3f0 15 128GB" />
          <span>\uc544\uc774\ud3f0 15 128GB</span>
          <strong>650,000\uc6d0</strong>
        </a>
        """

        candidates = extract_dom_candidates(html)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].price_text, "650,000\uc6d0")
        self.assertEqual(candidates[0].product_url, "/product/1")

    def test_dom_link_block_with_combined_title_and_price(self):
        html = """
        <a href="/product/2">\uc544\uc774\ud3f015 \ube14\ub8e8 256GB \uae09\ucc98 400,000\uc6d0 36\ubd84 \uc804</a>
        """

        candidates = extract_dom_candidates(html)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].product_name, "\uc544\uc774\ud3f015 \ube14\ub8e8 256GB \uae09\ucc98")
        self.assertEqual(candidates[0].price_text, "400,000\uc6d0")

    def test_dom_parent_block_candidate_when_price_is_outside_anchor(self):
        html = """
        <div>
          <a href="/product/232709086"><img src="/p.jpg" alt="\uc544\uc774\ud3f015 \ube14\ub8e8 256GB" /></a>
          <p>\uc544\uc774\ud3f015 \ube14\ub8e8 256GB \uae09\ucc98</p>
          <strong>400,000\uc6d0</strong>
        </div>
        """

        candidates = extract_dom_candidates(html)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].product_url, "/product/232709086")
        self.assertEqual(candidates[0].price_text, "400,000\uc6d0")

    def test_danawa_like_product_fixture(self):
        html = """
        <li>
          <a href="https://prod.danawa.com/info/?pcode=102124202">
            <img src="https://img.danawa.com/prod.jpg" alt="\uc0bc\uc131\uc804\uc790 \uac24\ub7ed\uc2dcS25 256GB, \uc790\uae09\uc81c" />
          </a>
          <p>\uc0bc\uc131\uc804\uc790 \uac24\ub7ed\uc2dcS25 256GB, \uc790\uae09\uc81c</p>
          <span>1,077,870\uc6d0</span>
        </li>
        """

        candidates = extract_dom_candidates(
            html,
            product_url_hints=("prod.danawa.com/info/", "pcode="),
        )

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].product_url, "https://prod.danawa.com/info/?pcode=102124202")
        self.assertEqual(candidates[0].price_text, "1,077,870\uc6d0")
        self.assertGreaterEqual(candidates[0].confidence, 3)

    def test_price_text_is_not_selected_as_product_name(self):
        html = """
        <li>
          <a href="https://prod.danawa.com/info/?pcode=102126383">1,473,160\uc6d0</a>
          <a href="https://prod.danawa.com/info/?pcode=102126383" title="\uc0bc\uc131\uc804\uc790 \uac24\ub7ed\uc2dcS25 5G 256GB \uc790\uae09\uc81c">
            \uc0bc\uc131\uc804\uc790 \uac24\ub7ed\uc2dcS25 5G 256GB \uc790\uae09\uc81c
          </a>
        </li>
        """

        candidates = extract_dom_candidates(
            html,
            product_url_hints=("prod.danawa.com/info/", "pcode="),
            query="\uac24\ub7ed\uc2dc S25",
        )

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].product_name, "\uc0bc\uc131\uc804\uc790 \uac24\ub7ed\uc2dcS25 5G 256GB \uc790\uae09\uc81c")
        self.assertNotEqual(candidates[0].product_name, "1,473,160")

    def test_img_src_and_lazy_image_attributes_are_extracted(self):
        html = """
        <ul>
          <li>
            <a href="https://prod.danawa.com/info/?pcode=1">
              <img src="https://img.danawa.com/prod1.jpg" alt="\uc0bc\uc131 \uac24\ub7ed\uc2dcS25" />
            </a>
            <span>1,077,870\uc6d0</span>
          </li>
          <li>
            <a href="https://prod.danawa.com/info/?pcode=2">
              <img data-lazy-src="/prod2.jpg" alt="\uc0bc\uc131 \uac24\ub7ed\uc2dcS25 \ud50c\ub7ec\uc2a4" />
            </a>
            <span>1,177,870\uc6d0</span>
          </li>
        </ul>
        """

        candidates = extract_dom_candidates(html, product_url_hints=("prod.danawa.com/info/", "pcode="))

        self.assertEqual(candidates[0].image_url, "https://img.danawa.com/prod1.jpg")
        self.assertEqual(candidates[1].image_url, "/prod2.jpg")

    def test_relative_image_url_is_normalized_to_absolute(self):
        html = """
        <li>
          <a href="https://prod.danawa.com/info/?pcode=2">
            <img data-lazy-src="/prod2.jpg" alt="\uc0bc\uc131 \uac24\ub7ed\uc2dcS25 \ud50c\ub7ec\uc2a4" />
          </a>
          <span>1,177,870\uc6d0</span>
        </li>
        """
        candidate = extract_dom_candidates(html, product_url_hints=("prod.danawa.com/info/", "pcode="))[0]

        product = normalize_candidate(
            candidate,
            SourceMetadata(source="danawa", display_name="Danawa", default_condition="new"),
            "https://search.danawa.com/dsearch.php?query=s25",
        )

        self.assertEqual(product.image_url, "https://search.danawa.com/prod2.jpg")

    def test_price_only_description_is_suppressed(self):
        html = """
        <li>
          <a href="https://prod.danawa.com/info/?pcode=102126383">1,473,160\uc6d0</a>
        </li>
        """

        candidates = extract_dom_candidates(html, product_url_hints=("prod.danawa.com/info/", "pcode="))

        self.assertEqual(candidates, [])

    def test_placeholder_href_price_anchor_is_not_a_product_candidate(self):
        html = """
        <a href="#">\ucd9c\uc2dc\uac00: 1,698,400\uc6d0</a>
        """

        candidates = extract_dom_candidates(html, product_url_hints=("prod.danawa.com/info/", "pcode="))

        self.assertEqual(candidates, [])


if __name__ == "__main__":
    unittest.main()
