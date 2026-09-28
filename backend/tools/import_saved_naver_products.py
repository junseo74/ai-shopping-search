import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    from backend.db import ProductRepository
    from backend.importers import ProductFileImporter
    from backend.models import CollectionRun, PlatformType
except ImportError:  # pragma: no cover - supports running from backend dir.
    from db import ProductRepository
    from importers import ProductFileImporter
    from models import CollectionRun, PlatformType


DEFAULT_DATA_SOURCE = "saved_html_import"


def import_saved_naver_products(
    file_path: str | Path,
    db_path: Optional[str | Path] = None,
    source_url: Optional[str] = None,
    source_observed_at: Optional[datetime] = None,
    data_source: str = DEFAULT_DATA_SOURCE,
    limit: Optional[int] = None,
) -> dict[str, object]:
    path = Path(file_path)
    observed_at = source_observed_at or datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
    products = ProductFileImporter().load(
        file_path=path,
        data_source=data_source,
        source_url=source_url,
        source_observed_at=observed_at,
        platform=PlatformType.NAVER_SHOPPING,
        limit=limit,
    )
    repository = ProductRepository(db_path)
    saved = repository.add_products_skip_duplicate_urls(products)
    repository.record_collection_run(
        CollectionRun(
            source_name=data_source,
            platform=PlatformType.NAVER_SHOPPING,
            status="success",
            product_count=len(saved),
        )
    )
    return {
        "status": "success",
        "read_count": len(products),
        "saved_count": len(saved),
        "skipped_count": len(products) - len(saved),
        "data_source": data_source,
        "platform": PlatformType.NAVER_SHOPPING.value,
        "source_url": str(products[0].source_url) if products and products[0].source_url else source_url,
        "source_observed_at": observed_at.isoformat(),
    }


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def main() -> None:
    parser = argparse.ArgumentParser(description="Import saved Naver Shopping JSON into SQLite.")
    parser.add_argument("file_path", help="Path to naver_real_products.json or another saved extraction JSON.")
    parser.add_argument("--db-path", help="SQLite DB path. Defaults to SHOPPING_DB_PATH or backend/data/products.db.")
    parser.add_argument("--source-url", help="Original saved search URL.")
    parser.add_argument("--source-observed-at", help="Extraction timestamp in ISO-8601 format.")
    parser.add_argument("--data-source", default=DEFAULT_DATA_SOURCE)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    result = import_saved_naver_products(
        file_path=args.file_path,
        db_path=args.db_path,
        source_url=args.source_url,
        source_observed_at=_parse_datetime(args.source_observed_at),
        data_source=args.data_source,
        limit=args.limit,
    )
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
