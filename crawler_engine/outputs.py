from __future__ import annotations

import json
from pathlib import Path

from .models import CrawlResult


def result_to_json(result: CrawlResult, indent: int = 2) -> str:
    return json.dumps(result.to_dict(), ensure_ascii=False, indent=indent)


def save_result(result: CrawlResult, output_path: Path | str) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(result_to_json(result), encoding="utf-8")
    return path
