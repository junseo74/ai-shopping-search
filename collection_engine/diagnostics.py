"""Offline source readiness. This module never constructs a collector."""
import argparse
import json
from datetime import datetime, timezone

from .registry import credential_presence, policies


# Capabilities describe implemented routes, independently of policy approval,
# credential presence, service availability, and historical live evidence.
CAPABILITIES = {
    "ebay_browse": ("official_api", True, True, "Configure developer credentials and approved production access."),
    "apple_books_lookup": ("isbn_lookup", True, False, "Supply ISBN-10/13; current robots policy must allow lookup."),
    "yes24_api": ("official_api", True, False, "Configure YES24_API_KEY; review caching and catalog reuse terms."),
    "yahoo_shopping": ("official_api", True, True, "Configure Client ID and review source policy before enabling lookup."),
    "rakuten_ichiba": ("official_api", True, True, "Configure application ID/access key; verify current API and allowed app domain."),
    "bestbuy_products": ("official_api", True, True, "Configure API key; review comparison-service purpose and source policy."),
    "elevenst": ("xml_api_blocked", False, False, "Existing API uses HTTP. Verify official HTTPS and usage permission before enabling."),
    "danawa": ("saved_html", False, False, "Supply legitimately held HTML; official MCP connector is not an engine adapter."),
    "musinsa": ("saved_html", False, False, "Supply legitimately held HTML; consumer catalog API permission is unverified."),
    "29cm": ("saved_html", False, False, "Partner product-management API is separate from public catalog search."),
    "kurly": ("saved_html", False, False, "Logistics API is separate from catalog search; use approved saved HTML."),
    "lotteon": ("saved_html", False, False, "Seller-management API access does not grant a marketplace catalog feed."),
    "joongna": ("saved_html", False, False, "Legacy internal API is not authorized; supply approved saved HTML only."),
    "approved_html": ("approved_html", True, False, "Requires explicitly approved URLs, selectors, reuse permission and robots allowance."),
    "shopping_auto": ("per_source_config", True, False, "Each nested source needs approval, configuration and its own credentials."),
    "test_fixture": ("local_synthetic", False, False, "Local test data only; not evidence of real collection."),
}


def diagnose(source=None, environ=None):
    config = policies()
    if source is not None and source not in config:
        raise ValueError("Unknown source")
    rows = []
    for name, policy in config.items():
        if source is not None and name != source:
            continue
        route, live, pagination, preparation = CAPABILITIES.get(name,
            ("unregistered", False, False, "Register and verify an adapter before use."))
        presence = credential_presence(policy, environ=environ)
        blockers = []
        if not live:
            blockers.append("live_adapter_unavailable")
        if not policy.lookup_allowed:
            blockers.append("policy_restriction")
        if not all(presence.values()):
            blockers.append("credentials_missing")
        if name in ("approved_html", "shopping_auto"):
            blockers.append("source_configuration_review_required")
        rows.append({"source": name, "method": policy.method, "route": route,
            "live_supported": live, "pagination_supported": pagination,
            "credential_presence": presence, "lookup_allowed": policy.lookup_allowed,
            "ready_for_explicit_live_check": not blockers, "blockers": blockers,
            "preparation": preparation, "validation_limit": policy.validation_limit,
            "retention_seconds": policy.retention_seconds, "terms_url": policy.terms_url,
            "live_verified_this_run": False})
    return {"network_used": False, "checked_at": datetime.now(timezone.utc).isoformat(),
        "sources": rows, "test_command": "python -m pytest tests -q",
        "live_check_command": "python -m collection_engine --live --source SOURCE --query QUERY --job-id NEW_ID --max-items 1 --page-size 1 --output OUTPUT"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", help="Filter to one registered source")
    args = parser.parse_args(argv)
    try:
        result = diagnose(args.source)
    except ValueError:
        parser.error("Unknown source")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
