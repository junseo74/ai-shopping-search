"""Offline readiness by default; explicit --live runs two bounded checks."""
from datetime import datetime, timezone
import argparse
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import sys
import subprocess

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dotenv import dotenv_values
from collection_engine.registry import build_adapter, credential_presence, policies
from collection_engine.runner import CollectionRunner
from collection_engine.storage import FileState, JsonlSink, atomic_json


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Explicitly allow one eBay and one Apple product lookup")
    args = parser.parse_args(argv)
    if not args.live:
        from collection_engine.diagnostics import main as diagnose_main
        return diagnose_main([])
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    directory = ROOT / "samples/engine_validation" / stamp
    directory.mkdir(parents=True)
    config = policies()
    result = {"checked_at": datetime.now(timezone.utc).isoformat(), "branch": subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip(),
              "baseline_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(), "sites": [], "readiness": [], "database_connected": False,
              "bulk_collection_performed": False, "raw_projection_only": True}
    original_db = ROOT / "backend/data/products.db"
    before = hashlib.sha256(original_db.read_bytes()).hexdigest() if original_db.exists() else None
    for source, query in (("ebay_browse", "keyboard"), ("apple_books_lookup", "9780316069359")):
        policy = config[source]
        presence = credential_presence(policy)
        entry = {"source": source, "credential_presence": presence, "raw_comparisons": [], "products": []}
        if not all(presence.values()):
            entry.update(status="blocked", category="credentials_missing")
            result["sites"].append(entry)
            continue
        adapter = build_adapter(source)
        sink = JsonlSink(directory / source / "outbox")
        runner = CollectionRunner(adapter, policy, FileState(directory / source / "state"), sink)
        run = runner.run(query, source + "-" + stamp, max_items=1, page_size=1, max_pages=1)
        entry["run"] = run
        records = list(sink.iter_unexpired(datetime.now(timezone.utc)))
        if source == "ebay_browse":
            projections = adapter.last_page_projection
            entry["product_http_requests"] = adapter.transport.request_count
        else:
            projections = [{"itemId": str(row.get("trackId")), "title": row.get("trackName"),
                            "price": {"value": row.get("price"), "currency": row.get("currency")},
                            "itemWebUrl": row.get("trackViewUrl")} for row in
                           (adapter.collector.last_response or {}).get("results", []) if row.get("kind") == "ebook"]
            entry["robots_audit"] = adapter.collector.last_audit
            entry["product_http_requests"] = int(bool(adapter.collector.last_audit and "http_status" in adapter.collector.last_audit))
        for record in records:
            raw = next((row for row in projections if str(row.get("itemId")) == record["source_product_id"]), None)
            if raw is None:
                continue
            normalized = record["product"]
            checks = {"name": normalized["product_name"] == raw["title"],
                      "price": Decimal(str(normalized["price"])) == Decimal(str(raw["price"]["value"])),
                      "currency": normalized["currency"] == raw["price"]["currency"],
                      "url": normalized["product_url"] == raw["itemWebUrl"]}
            entry["raw_comparisons"].append({"source_product_id": record["source_product_id"], "checks": checks,
                                              "raw_projection": raw})
        entry["products"] = records
        entry["status"] = "verified" if (run["status"] == "completed" and records
            and len(entry["raw_comparisons"]) == len(records)
            and all(all(row["checks"].values()) for row in entry["raw_comparisons"])) else "failed"
        result["sites"].append(entry)
    for source in ("yes24_api", "elevenst", "yahoo_shopping", "rakuten_ichiba", "bestbuy_products"):
        policy = config[source]
        presence = credential_presence(policy)
        result["readiness"].append({"source": source, "credential_presence": presence,
            "product_request_made": False, "credentials_missing": not all(presence.values()),
            "policy_review_required": not policy.lookup_allowed})
    result["attempted_sites"] = sum(bool(row.get("run")) for row in result["sites"])
    result["verified_sites"] = sum(row["status"] == "verified" for row in result["sites"])
    result["verified_products"] = sum(len(row["products"]) for row in result["sites"] if row["status"] == "verified")
    result["live_success_rate"] = result["verified_sites"] / result["attempted_sites"] if result["attempted_sites"] else None
    after = hashlib.sha256(original_db.read_bytes()).hexdigest() if original_db.exists() else None
    result["existing_db_hash_unchanged"] = before == after
    settings = dotenv_values(ROOT / ".env")
    values = [value for key, value in settings.items() if value and any(
        fragment in key.upper() for fragment in ("KEY", "SECRET", "TOKEN", "CLIENT_ID"))]
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    artifacts = list(directory.rglob("*.json")) + list(directory.rglob("*.jsonl"))
    texts = [payload] + [path.read_text(encoding="utf-8") for path in artifacts]
    assert not any(value in text for value in values for text in texts), "Sensitive value detected; do not print artifacts"
    result["secret_scan_passed"] = True
    atomic_json(directory / "verification.json", result)
    print(json.dumps({"verified_sites": result["verified_sites"], "verified_products": result["verified_products"],
                      "success_rate": result["live_success_rate"], "db_unchanged": before == after,
                      "secret_scan_passed": True, "evidence": str((directory / "verification.json").relative_to(ROOT))}))
    return 0 if result["verified_sites"] == 2 else 1


if __name__ == "__main__":
    raise SystemExit(main())
