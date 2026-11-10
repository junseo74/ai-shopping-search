import json
import os
from pathlib import Path

from .contracts import CollectionError, SourcePolicy
from .adapters import BackendCollectorAdapter, PagedCollectorAdapter


def policies(path=None):
    document = json.loads(Path(path or Path(__file__).with_name("source_policies.json")).read_text(encoding="utf-8"))
    result = {}
    for row in document["sources"]:
        row = dict(row)
        for field in ("credential_env", "purposes", "omitted_fields"):
            if field in row:
                row[field] = tuple(row[field])
        policy = SourcePolicy(**row)
        if policy.source in result:
            raise ValueError("Duplicate source policy")
        result[policy.source] = policy
    return result


def build_adapter(source, saved_html=None):
    if saved_html is not None:
        from .adapters import LegacySavedHtmlAdapter
        if source not in ("danawa", "musinsa", "kurly", "29cm", "lotteon", "joongna", "elevenst"):
            raise CollectionError("saved_html_source_not_supported")
        return LegacySavedHtmlAdapter(source, saved_html)
    if source == "elevenst":
        # Policy edits or credentials alone must not send keys over the legacy
        # HTTP endpoint. Enable only after an official secure route is verified.
        raise CollectionError("secure_endpoint_unverified")
    if source in ("apple_books_lookup", "yes24_api"):
        from backend.collectors.apple_books import AppleBooksLookupCollector
        from backend.collectors.yes24 import Yes24ProductCollector
        from .transport import HttpTransport
        factory = AppleBooksLookupCollector if source == "apple_books_lookup" else Yes24ProductCollector
        return BackendCollectorAdapter(factory(transport=HttpTransport()))
    if source == "ebay_browse":
        from .adapters import EbayPagedAdapter
        return EbayPagedAdapter()
    if source in ("yahoo_shopping", "rakuten_ichiba", "bestbuy_products"):
        from backend.collectors.official_catalogs import YahooShoppingCollector, RakutenIchibaCollector, BestBuyProductsCollector
        factory = {"yahoo_shopping": YahooShoppingCollector, "rakuten_ichiba": RakutenIchibaCollector,
                   "bestbuy_products": BestBuyProductsCollector}[source]
        return PagedCollectorAdapter(factory())
    from backend.collectors import ApprovedHtmlProductCollector, ShoppingAutoCollector, TestFixtureCollector
    factory = {"approved_html": ApprovedHtmlProductCollector, "shopping_auto": ShoppingAutoCollector,
               "test_fixture": TestFixtureCollector}.get(source)
    if factory:
        return BackendCollectorAdapter(factory())
    # Legacy adapters require an explicitly supplied saved HTML artifact. Do not
    # automatically execute the old internal APIs or an unrestricted browser.
    raise CollectionError("approved_input_or_adapter_required")


def credential_presence(policy, environ=None):
    """Return flags only; never expose values or load another worktree's .env."""
    if environ is None:
        from dotenv import dotenv_values
        configured = dotenv_values(Path(__file__).resolve().parents[1] / ".env")
        configured.update(os.environ)
    else:
        configured = environ
    return {key: bool(str(configured.get(key) or "").strip()) for key in policy.credential_env}
