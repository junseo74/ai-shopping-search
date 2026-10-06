import unittest

from crawler_engine.aggregation import aggregate_candidates, choose_representative_name, infer_condition, product_identity
from crawler_engine.engine import CrawlerEngine
from crawler_engine.models import CrawlRequest, ProductCandidate, SourceMetadata
from crawler_engine.sites.danawa import DanawaSource


class StaticEngine(CrawlerEngine):
    def __init__(self, html: str):
        super().__init__()
        self.html = html

    def render_page(self, url: str) -> str:
        return self.html


class AggregationTest(unittest.TestCase):
    def test_same_pcode_fragments_merge_into_one_candidate(self):
        metadata = DanawaSource.metadata
        candidates = [
            ProductCandidate(
                product_name="\ud6c4\uba74:2\uc5b5 \ud654\uc18c+1,000\ub9cc\ud654\uc18c",
                price_text="1,473,160\uc6d0",
                product_url="https://prod.danawa.com/info/?pcode=102126383&keyword=x",
                description="\ud6c4\uba74:2\uc5b5 \ud654\uc18c / \uc0bc\uc131\uc804\uc790 / \uac24\ub7ed\uc2dc / S25 / \uc6b8\ud2b8\ub77c 256GB, \uc790\uae09\uc81c",
            ),
            ProductCandidate(
                product_name="New \uc0c8\ub85c\uc6cc\uc9c4 \uc0c1\ud488\ube44\uad50 \uae30\ub2a5",
                price_text="1,473,160\uc6d0",
                product_url="https://prod.danawa.com/info/?pcode=102126383&cate=123",
                description="New \uc0c8\ub85c\uc6cc\uc9c4 \uc0c1\ud488\ube44\uad50 \uae30\ub2a5 / \uc744 \uc774\uc6a9\ud574\ubcf4\uc138\uc694. / \ub2eb\uae30 / 77\ubab0",
            ),
        ]

        aggregated = aggregate_candidates(candidates, metadata, "https://search.danawa.com/dsearch.php", query="\uac24\ub7ed\uc2dc S25")

        self.assertEqual(len(aggregated), 1)
        self.assertEqual(aggregated[0].product_url, "https://prod.danawa.com/info/?pcode=102126383")
        self.assertEqual(aggregated[0].price, 1473160)

    def test_ui_option_and_spec_fragments_do_not_beat_full_name(self):
        metadata = DanawaSource.metadata
        candidates = [
            ProductCandidate(
                product_name="\ud2f0\ud0c0\ub284 \ube14\ub799",
                price_text="1,473,160\uc6d0",
                product_url="https://prod.danawa.com/info/?pcode=102126383",
            ),
            ProductCandidate(
                product_name="\ud6c4\uba74:2\uc5b5 \ud654\uc18c+1,000\ub9cc\ud654\uc18c+5,000\ub9cc\ud654\uc18c",
                price_text="1,473,160\uc6d0",
                product_url="https://prod.danawa.com/info/?pcode=102126383",
            ),
            ProductCandidate(
                product_name="\uc0bc\uc131\uc804\uc790 \uac24\ub7ed\uc2dc S25 \uc6b8\ud2b8\ub77c 256GB \uc790\uae09\uc81c",
                price_text="1,473,160\uc6d0",
                product_url="https://prod.danawa.com/info/?pcode=102126383",
            ),
        ]

        aggregated = aggregate_candidates(candidates, metadata, "https://search.danawa.com/dsearch.php", query="\uac24\ub7ed\uc2dc S25")

        self.assertEqual(aggregated[0].product_name, "\uc0bc\uc131\uc804\uc790 \uac24\ub7ed\uc2dc S25 \uc6b8\ud2b8\ub77c 256GB \uc790\uae09\uc81c")

    def test_description_fragments_can_build_representative_name(self):
        metadata = DanawaSource.metadata
        candidates = [
            ProductCandidate(
                product_name="\ud2f0\ud0c0\ub284 \ud654\uc774\ud2b8\uc2e4\ubc84",
                price_text="1,473,160\uc6d0",
                product_url="https://prod.danawa.com/info/?pcode=102126383",
                description="\uc0bc\uc131\uc804\uc790 / \uac24\ub7ed\uc2dc / S25 / \uc6b8\ud2b8\ub77c 256GB, \uc790\uae09\uc81c",
            )
        ]

        aggregated = aggregate_candidates(candidates, metadata, "https://search.danawa.com/dsearch.php", query="\uac24\ub7ed\uc2dc S25")

        self.assertEqual(aggregated[0].product_name, "\uc0bc\uc131\uc804\uc790 \uac24\ub7ed\uc2dc S25 \uc6b8\ud2b8\ub77c 256GB, \uc790\uae09\uc81c")

    def test_direct_product_name_beats_long_synthetic_description_name(self):
        metadata = DanawaSource.metadata
        direct_name = "\uc0bc\uc131\uc804\uc790 \uac24\ub7ed\uc2dc S25 \uc6b8\ud2b8\ub77c 256GB, \uc790\uae09\uc81c"
        candidates = [
            ProductCandidate(
                product_name=direct_name,
                price_text="1,473,100\uc6d0",
                product_url="https://prod.danawa.com/info/?pcode=102126383",
                description=(
                    "\uac24\ub7ed\uc2dcS25 \uc6b8\ud2b8\ub77c 256GB, \uc790\uae09\uc81c / "
                    f"{direct_name} / "
                    "\ucd9c\uc2dc\uac00: 1,698,400\uc6d0"
                ),
            )
        ]

        aggregated = aggregate_candidates(candidates, metadata, "https://search.danawa.com/dsearch.php", query="\uac24\ub7ed\uc2dc S25")

        self.assertEqual(aggregated[0].product_name, direct_name)

    def test_price_label_text_is_not_a_name_candidate(self):
        name = choose_representative_name(
            [
                "\ucd9c\uc2dc\uac00: 1,698,400\uc6d0",
                "\ud310\ub9e4\uac00: 100,000\uc6d0",
                "\uac00\uaca9: 50,000\uc6d0",
            ]
        )

        self.assertIsNone(name)

    def test_condition_inference_used_evidence(self):
        self.assertEqual(infer_condition(["\ucd5c\uc0c1\uae09,\uc911\uace0"], "new"), "used")
        self.assertEqual(infer_condition(["S\ub4f1\uae09,\uc911\uace0"], "new"), "used")

    def test_source_default_new_loses_to_explicit_used_evidence(self):
        metadata = DanawaSource.metadata
        aggregated = aggregate_candidates(
            [
                ProductCandidate(
                    product_name="\ucd5c\uc0c1\uae09,\uc911\uace0",
                    price_text="900,000\uc6d0",
                    product_url="https://prod.danawa.com/info/?pcode=102126383",
                    description="19\ubab0 / 1\uc704 / \ucd5c\uc0c1\uae09,\uc911\uace0",
                )
            ],
            metadata,
            "https://search.danawa.com/dsearch.php",
            include_used=True,
        )

        self.assertEqual(aggregated[0].condition, "used")

    def test_include_used_filter_for_mixed_source(self):
        metadata = DanawaSource.metadata
        candidates = [
            ProductCandidate(
                product_name="\ucd5c\uc0c1\uae09,\uc911\uace0",
                price_text="900,000\uc6d0",
                product_url="https://prod.danawa.com/info/?pcode=1",
                description="\ucd5c\uc0c1\uae09,\uc911\uace0",
            )
        ]

        excluded = aggregate_candidates(candidates, metadata, "https://search.danawa.com/dsearch.php", include_used=False)
        included = aggregate_candidates(candidates, metadata, "https://search.danawa.com/dsearch.php", include_used=True)

        self.assertEqual(excluded, [])
        self.assertEqual(len(included), 1)

    def test_group_image_candidate_is_used(self):
        metadata = DanawaSource.metadata
        aggregated = aggregate_candidates(
            [
                ProductCandidate(
                    product_name="\uc0bc\uc131\uc804\uc790 \uac24\ub7ed\uc2dc S25 256GB \uc790\uae09\uc81c",
                    price_text="1,077,870\uc6d0",
                    product_url="https://prod.danawa.com/info/?pcode=102124202",
                ),
                ProductCandidate(
                    product_name="\ud61c\ud0dd \ucd5c\uc800\uac00",
                    price_text="1,077,870\uc6d0",
                    product_url="https://prod.danawa.com/info/?pcode=102124202",
                    image_url="https://img.danawa.com/prod.jpg",
                ),
            ],
            metadata,
            "https://search.danawa.com/dsearch.php",
        )

        self.assertEqual(aggregated[0].image_url, "https://img.danawa.com/prod.jpg")

    def test_product_identity_uses_pcode_not_search_params(self):
        metadata = DanawaSource.metadata
        first = ProductCandidate(product_url="https://prod.danawa.com/info/?pcode=102126383&keyword=s25")
        second = ProductCandidate(product_url="https://prod.danawa.com/info/?cate=1&pcode=102126383")

        self.assertEqual(
            product_identity(first, metadata, "https://search.danawa.com"),
            product_identity(second, metadata, "https://search.danawa.com"),
        )

    def test_engine_filters_used_after_aggregation(self):
        html = """
        <li>
          <a href="https://prod.danawa.com/info/?pcode=1">\uc0bc\uc131\uc804\uc790 \uac24\ub7ed\uc2dc S25 256GB \uc790\uae09\uc81c</a>
          <span>1,077,870\uc6d0</span>
        </li>
        <li>
          <a href="https://prod.danawa.com/info/?pcode=2">\ucd5c\uc0c1\uae09,\uc911\uace0</a>
          <span>900,000\uc6d0</span>
        </li>
        """

        result = StaticEngine(html).crawl(CrawlRequest(query="\uac24\ub7ed\uc2dc S25", include_used=False), source_name="danawa")

        self.assertEqual(len(result.products), 1)
        self.assertEqual(result.products[0].condition, "new")

    def test_engine_keeps_used_when_requested(self):
        html = """
        <li>
          <a href="https://prod.danawa.com/info/?pcode=2">\ucd5c\uc0c1\uae09,\uc911\uace0</a>
          <span>900,000\uc6d0</span>
        </li>
        """

        result = StaticEngine(html).crawl(CrawlRequest(query="\uac24\ub7ed\uc2dc S25", include_used=True), source_name="danawa")

        self.assertEqual(len(result.products), 1)
        self.assertEqual(result.products[0].condition, "used")


if __name__ == "__main__":
    unittest.main()
