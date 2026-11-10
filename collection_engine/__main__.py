"""Run bounded validation without importing backend.main or any DB module."""
import argparse
from datetime import datetime, timezone
import json
import sys
from pathlib import Path

from .contracts import CollectionError
from .registry import build_adapter, credential_presence, policies
from .runner import CollectionRunner
from .storage import FileState, JsonlSink, atomic_json, digest


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] == "diagnose":
        from .diagnostics import main as diagnose_main
        return diagnose_main(argv[1:] if argv else [])
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Explicitly allow a bounded live API check")
    parser.add_argument("--source", required=True)
    parser.add_argument("--query", required=True)
    parser.add_argument("--job-id", required=True, help="Reuse exactly to resume; use a new ID for a refresh")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-items", type=int, default=3)
    parser.add_argument("--page-size", type=int, default=3)
    parser.add_argument("--max-pages", type=int, default=1)
    args = parser.parse_args(argv)
    if not args.live:
        parser.error("Live collection requires --live; use 'python -m collection_engine diagnose' for offline readiness")
    if not 1 <= args.max_items or not 1 <= args.page_size <= 1000 or args.max_pages < 1:
        parser.error("Use positive item/page limits and page-size at most 1000")
    policy = policies().get(args.source)
    if policy is None:
        parser.error("Unknown source")
    presence = credential_presence(policy)
    result = {"source": args.source, "credential_presence": presence,
              "checked_at": datetime.now(timezone.utc).isoformat()}
    try:
        policy.check("validation", args.max_items)
        if not all(presence.values()):
            raise CollectionError("credentials_missing")
        runner = CollectionRunner(build_adapter(args.source), policy,
            FileState(args.output / "state"), JsonlSink(args.output / "outbox"))
        result.update(runner.run(args.query, args.job_id, max_items=args.max_items,
                                page_size=args.page_size, max_pages=args.max_pages))
    except CollectionError as error:
        result.update(status="blocked", error_category=error.category, http_status=error.http_status)
    except Exception as error:
        result.update(status="failed", error_category="processing_error", error_type=type(error).__name__)
    atomic_json(args.output / "runs" / (digest(args.job_id) + ".json"), result)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("status") in ("completed", "paused_at_page_budget") else 1


if __name__ == "__main__":
    raise SystemExit(main())
