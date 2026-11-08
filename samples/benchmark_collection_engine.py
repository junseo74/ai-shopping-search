"""Small synthetic reference benchmark; never counts as real collected products."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
import time
import tracemalloc

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.models import Product
from collection_engine.contracts import Offer, Page, SourcePolicy
from collection_engine.runner import CollectionRunner
from collection_engine.storage import FileState, JsonlSink, atomic_json


class SyntheticAdapter:
    source = "synthetic_benchmark"

    def __init__(self, total=1000, changed=False):
        self.total, self.changed = total, changed

    def fetch_page(self, query, cursor, limit, since=None):
        start = int(cursor or "0")
        offers = []
        for index in range(start, min(start + limit, self.total)):
            identity = index - 1 if index % 10 == 9 else index
            price = 11 if self.changed and identity % 50 == 0 else 10
            product = Product(product_name=f"SYNTHETIC BENCHMARK {identity}", price=price,
                currency="USD", product_url=f"https://example.com/synthetic/{identity}",
                platform="test", data_source=self.source)
            offers.append(Offer(product, str(identity), str(identity)))
        end = start + len(offers)
        return Page(offers, str(end) if end < self.total else None)


def main():
    total = 1000
    policy = SourcePolicy("synthetic_benchmark", "local_synthetic", True, "local://synthetic-test",
                          purposes=("benchmark",), bulk_approved=True, synthetic=True)
    tracemalloc.start()
    start = time.perf_counter()
    runtime = ROOT / ".validation_runtime"
    runtime.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="shopping-synthetic-benchmark-", dir=runtime) as directory:
        state = FileState(Path(directory) / "state")
        sink = JsonlSink(Path(directory) / "outbox")
        runs = []
        for job, changed in (("initial", False), ("unchanged-refresh", False), ("price-update", True)):
            runner = CollectionRunner(SyntheticAdapter(total, changed), policy, state, sink)
            runs.append(runner.run("synthetic", job, max_items=total, page_size=100,
                                   max_pages=10, purpose="benchmark"))
        peak = tracemalloc.get_traced_memory()[1]
        outbox_bytes = sum(path.stat().st_size for path in Path(directory).rglob("*.jsonl"))
    elapsed = time.perf_counter() - start
    tracemalloc.stop()
    assert [run["status"] for run in runs] == ["completed"] * 3
    assert [run["stats"]["emitted"] for run in runs] == [900, 0, 20]
    assert all(run["stats"]["duplicates"] == 100 for run in runs)
    result = {"synthetic": True, "real_product_count": 0, "external_requests": 0,
              "rows_per_pass": total, "passes": 3, "page_size": 100,
              "elapsed_seconds": round(elapsed, 3), "rows_processed_per_second": round(3000 / elapsed, 1),
              "peak_traced_python_bytes": peak, "outbox_bytes": outbox_bytes,
              "runs": runs, "checked_at": datetime.now(timezone.utc).isoformat(),
              "limitations": "Local single-writer reference; not an HTTP throughput, full process RSS, distributed or 3-million-row capacity test."}
    output = ROOT / "samples/engine_validation" / ("synthetic-benchmark-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json")
    atomic_json(output, result)
    print(json.dumps({key: value for key, value in result.items() if key not in ("runs", "limitations")}))
    print(str(output.relative_to(ROOT)))


if __name__ == "__main__":
    main()
