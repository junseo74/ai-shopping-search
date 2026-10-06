import json
import unittest

from crawler_engine.aggregation import aggregate_candidates, product_identity
from crawler_engine.engine import CrawlerEngine
from crawler_engine.extractors.musinsa import extract_musinsa_candidates
from crawler_engine.models import CrawlRequest, ProductCandidate
from crawler_engine.sources import available_sources, select_sources


def _next_data_html(items):
    payload = {
        "props": {
            "pageProps": {
                "dehydratedState": {
                    "queries": [
                        {
                            "state": {
                                "data": {
                                    "pages": [
                                        {
                                            "items": items,
                                            "pagination": {
                                                "size": 60,
                                                "hasNext": True,
                                                "totalPages": 39,
                                            },
                                        }
                                    ]
                                }
                            }
                        }
                    ]
                }
            }
        }
    }
    return (
        '<html><body><script id="__NEXT_DATA__" type="application/json">'
        + json.dumps(payload)
        + "</script></body></html>"
    )


def _item(**overrides):
    item = {
        "goodsNo": 7261903,
        "goodsName": "ACG Zegama Trail GORE-TEX M",
        "goodsLinkUrl": "https://www.musinsa.com/products/7261903",
        "thumbnail": "https://image.msscdn.net/images/goods_img/20260907/7261903/7261903_500.jpg",
        "normalPrice": 249000,
        "price": 249000,
        "couponPrice": None,
        "finalPrice": 249000,
        "finalDiscount": 0,
        "saleRate": 0,
        "couponSaleRate": 0,
        "brand": "nike",
        "brandName": "Nike",
        "brandLinkUrl": "https://www.musinsa.com/brand/nike",
        "isSoldOut": False,
        "isAd": False,
    }
    item.update(overrides)
    return item


class MusinsaSourceTest(unittest.TestCase):
    def test_musinsa_source_url_and_metadata(self):
        source = available_sources()["musinsa"]

        self.assertEqual(
            source.build_search_url(CrawlRequest(query="\ub098\uc774\ud0a4")),
            "https://www.musinsa.com/search/goods?keyword=%EB%82%98%EC%9D%B4%ED%82%A4&gf=A",
        )
        self.assertEqual(source.metadata.source, "musinsa")
        self.assertEqual(source.metadata.display_name, "MUSINSA")
        self.assertEqual(source.metadata.country, "KR")
        self.assertFalse(source.metadata.used_only)
        self.assertEqual(source.metadata.default_condition, "new")
        self.assertTrue(source.metadata.require_positive_price)

    def test_musinsa_runs_when_used_is_disabled(self):
        selected = select_sources(CrawlRequest(query="\ub098\uc774\ud0a4", include_used=False), "musinsa")

        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0].metadata.source, "musinsa")


class MusinsaExtractorTest(unittest.TestCase):
    def test_next_data_extracts_product_object_and_skips_experiment_object(self):
        html = _next_data_html(
            [
                _item(),
                {
                    "goodsNo": 9999999,
                    "experimentId": "plp-banner",
                    "experimentUrl": "https://example.test",
                    "contentsList": [],
                },
            ]
        )

        candidates = extract_musinsa_candidates(html)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].raw["goodsNo"], 7261903)

    def test_goods_fields_map_to_candidate(self):
        candidate = extract_musinsa_candidates(_next_data_html([_item()]))[0]

        self.assertEqual(candidate.product_name, "ACG Zegama Trail GORE-TEX M")
        self.assertEqual(candidate.seller, "Nike")
        self.assertEqual(candidate.product_url, "https://www.musinsa.com/products/7261903")
        self.assertEqual(
            candidate.image_url,
            "https://image.msscdn.net/images/goods_img/20260907/7261903/7261903_500.jpg",
        )
        self.assertEqual(candidate.condition, "new")
        self.assertEqual(candidate.source, "musinsa")
        self.assertEqual(candidate.country, "KR")
        self.assertEqual(candidate.currency, "KRW")
        self.assertIsNone(candidate.description)

    def test_final_price_is_preferred(self):
        candidate = extract_musinsa_candidates(
            _next_data_html([_item(finalPrice=114480, couponPrice=120000, price=127200, normalPrice=159000)])
        )[0]

        self.assertEqual(candidate.price, 114480)

    def test_coupon_price_fallback_when_final_price_is_missing(self):
        candidate = extract_musinsa_candidates(
            _next_data_html([_item(finalPrice=None, couponPrice=114480, price=127200, normalPrice=159000)])
        )[0]

        self.assertEqual(candidate.price, 114480)

    def test_price_fallback_when_coupon_price_is_missing(self):
        candidate = extract_musinsa_candidates(
            _next_data_html([_item(finalPrice=None, couponPrice=None, price=127200, normalPrice=159000)])
        )[0]

        self.assertEqual(candidate.price, 127200)

    def test_normal_price_fallback_when_sale_prices_are_missing(self):
        candidate = extract_musinsa_candidates(
            _next_data_html([_item(finalPrice=None, couponPrice=None, price=None, normalPrice=159000)])
        )[0]

        self.assertEqual(candidate.price, 159000)

    def test_invalid_and_zero_price_items_are_excluded(self):
        html = _next_data_html(
            [
                _item(finalPrice=0, couponPrice=0, price=0, normalPrice=0),
                _item(
                    goodsNo=6168644,
                    goodsLinkUrl="https://www.musinsa.com/products/6168644",
                    finalPrice="free",
                    couponPrice=None,
                    price=None,
                    normalPrice=None,
                ),
            ]
        )

        self.assertEqual(extract_musinsa_candidates(html), [])

    def test_brand_code_is_used_when_brand_name_is_missing(self):
        candidate = extract_musinsa_candidates(_next_data_html([_item(brandName=None, brand="nike")]))[0]

        self.assertEqual(candidate.seller, "nike")

    def test_same_goods_url_dedupes_by_canonical_identity(self):
        source = available_sources()["musinsa"]
        candidates = [
            ProductCandidate(product_name="Nike A", price=10000, product_url="https://www.musinsa.com/products/7261903"),
            ProductCandidate(product_name="Nike A", price=10000, product_url="https://www.musinsa.com/products/7261903?utm=ad"),
        ]

        identities = [product_identity(candidate, source.metadata, source.metadata.base_url) for candidate in candidates]
        aggregated = aggregate_candidates(candidates, source.metadata, source.metadata.base_url, query="nike")

        self.assertEqual(identities[0], identities[1])
        self.assertEqual(len(aggregated), 1)

    def test_engine_uses_site_specific_candidates_before_generic_extractors(self):
        html = _next_data_html([_item(finalPrice=114480, price=127200, normalPrice=159000)])
        html += '<a href="https://www.musinsa.com/products/7261903"><span>Bad DOM Name</span><strong>10\uc6d0</strong></a>'
        engine = CrawlerEngine()
        source = available_sources()["musinsa"]

        candidates = engine.extract_candidates(html, source.metadata, limit=20, query="\ub098\uc774\ud0a4")

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].product_name, "ACG Zegama Trail GORE-TEX M")
        self.assertEqual(candidates[0].price, 114480)


if __name__ == "__main__":
    unittest.main()
