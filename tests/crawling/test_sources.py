import unittest

from crawler_engine.models import CrawlRequest
from crawler_engine.sources import available_sources, select_sources


class SourcesTest(unittest.TestCase):
    def test_danawa_source_url_and_metadata(self):
        source = available_sources()["danawa"]

        self.assertEqual(
            source.build_search_url(CrawlRequest(query="\uac24\ub7ed\uc2dc S25")),
            "https://search.danawa.com/dsearch.php?query=%EA%B0%A4%EB%9F%AD%EC%8B%9C+S25",
        )
        self.assertFalse(source.metadata.used_only)
        self.assertEqual(source.metadata.default_condition, "new")

    def test_danawa_runs_when_used_is_disabled(self):
        selected = select_sources(CrawlRequest(query="\uac24\ub7ed\uc2dc S25", include_used=False), "danawa")

        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0].metadata.source, "danawa")


if __name__ == "__main__":
    unittest.main()
