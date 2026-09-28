import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator, Optional

try:
    from .models import CollectionRun, Product
except ImportError:
    from models import CollectionRun, Product


DEFAULT_DB_PATH = Path(__file__).resolve().parent / "data" / "products.db"


def get_database_path() -> Path:
    return Path(os.getenv("SHOPPING_DB_PATH", str(DEFAULT_DB_PATH)))


def _to_iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _from_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)


class ProductRepository:
    def __init__(self, db_path: Optional[Path | str] = None):
        self.db_path = Path(db_path) if db_path else get_database_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = self.connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_db(self) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_name TEXT NOT NULL,
                    price REAL,
                    original_price REAL,
                    shipping_fee REAL,
                    currency TEXT NOT NULL,
                    category TEXT,
                    seller TEXT,
                    platform TEXT NOT NULL,
                    product_url TEXT,
                    image_url TEXT,
                    condition TEXT NOT NULL,
                    region TEXT,
                    detail_description TEXT,
                    source_url TEXT,
                    source_license TEXT,
                    source_observed_at TEXT,
                    collected_at TEXT NOT NULL,
                    data_source TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS collection_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_name TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    status TEXT NOT NULL,
                    product_count INTEGER NOT NULL,
                    response_time_ms REAL NOT NULL,
                    error_message TEXT,
                    started_at TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_products_name ON products(product_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_products_source ON products(data_source)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_products_platform ON products(platform)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_products_url ON products(product_url)")
            self._ensure_column(conn, "products", "detail_description", "TEXT")
            self._ensure_column(conn, "products", "original_price", "REAL")
            self._ensure_column(conn, "products", "source_url", "TEXT")
            self._ensure_column(conn, "products", "source_license", "TEXT")
            self._ensure_column(conn, "products", "source_observed_at", "TEXT")
            self._ensure_nullable_seller(conn)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_products_name ON products(product_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_products_source ON products(data_source)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_products_platform ON products(platform)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_products_url ON products(product_url)")

    def _ensure_column(self, conn: sqlite3.Connection, table: str, column: str, column_type: str) -> None:
        columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if column not in columns:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")

    def _ensure_nullable_seller(self, conn: sqlite3.Connection) -> None:
        columns = conn.execute("PRAGMA table_info(products)").fetchall()
        seller = next((row for row in columns if row["name"] == "seller"), None)
        if not seller or not seller["notnull"]:
            return

        conn.execute(
            """
            CREATE TABLE products_migrated (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_name TEXT NOT NULL,
                price REAL,
                original_price REAL,
                shipping_fee REAL,
                currency TEXT NOT NULL,
                category TEXT,
                seller TEXT,
                platform TEXT NOT NULL,
                product_url TEXT,
                image_url TEXT,
                condition TEXT NOT NULL,
                region TEXT,
                detail_description TEXT,
                source_url TEXT,
                source_license TEXT,
                source_observed_at TEXT,
                collected_at TEXT NOT NULL,
                data_source TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            INSERT INTO products_migrated (
                id, product_name, price, original_price, shipping_fee, currency, category, seller,
                platform, product_url, image_url, condition, region,
                detail_description, source_url, source_license, source_observed_at,
                collected_at, data_source
            )
            SELECT
                id, product_name, price, original_price, shipping_fee, currency, category, seller,
                platform, product_url, image_url, condition, region,
                detail_description, source_url, source_license, source_observed_at,
                collected_at, data_source
            FROM products
            """
        )
        conn.execute("DROP TABLE products")
        conn.execute("ALTER TABLE products_migrated RENAME TO products")

    def add_products(self, products: Iterable[Product]) -> list[Product]:
        saved: list[Product] = []
        with self.connection() as conn:
            for product in products:
                cursor = conn.execute(
                    """
                    INSERT INTO products (
                        product_name, price, original_price, shipping_fee, currency, category, seller,
                        platform, product_url, image_url, condition, region,
                        detail_description, source_url, source_license, source_observed_at,
                        collected_at, data_source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        product.product_name,
                        product.price,
                        product.original_price,
                        product.shipping_fee,
                        product.currency,
                        product.category,
                        product.seller,
                        product.platform,
                        str(product.product_url) if product.product_url else None,
                        str(product.image_url) if product.image_url else None,
                        product.condition,
                        product.region,
                        product.detail_description,
                        str(product.source_url) if product.source_url else None,
                        product.source_license,
                        _to_iso(product.source_observed_at) if product.source_observed_at else None,
                        _to_iso(product.collected_at),
                        product.data_source,
                    ),
                )
                saved.append(product.model_copy(update={"id": cursor.lastrowid}))
        return saved

    def add_products_skip_duplicate_urls(self, products: Iterable[Product]) -> list[Product]:
        saved: list[Product] = []
        with self.connection() as conn:
            for product in products:
                product_url = str(product.product_url) if product.product_url else None
                if product_url and self._product_url_exists(conn, product_url):
                    continue
                cursor = conn.execute(
                    """
                    INSERT INTO products (
                        product_name, price, original_price, shipping_fee, currency, category, seller,
                        platform, product_url, image_url, condition, region,
                        detail_description, source_url, source_license, source_observed_at,
                        collected_at, data_source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        product.product_name,
                        product.price,
                        product.original_price,
                        product.shipping_fee,
                        product.currency,
                        product.category,
                        product.seller,
                        product.platform,
                        product_url,
                        str(product.image_url) if product.image_url else None,
                        product.condition,
                        product.region,
                        product.detail_description,
                        str(product.source_url) if product.source_url else None,
                        product.source_license,
                        _to_iso(product.source_observed_at) if product.source_observed_at else None,
                        _to_iso(product.collected_at),
                        product.data_source,
                    ),
                )
                saved.append(product.model_copy(update={"id": cursor.lastrowid}))
        return saved

    def _product_url_exists(self, conn: sqlite3.Connection, product_url: str) -> bool:
        row = conn.execute("SELECT 1 FROM products WHERE product_url = ? LIMIT 1", (product_url,)).fetchone()
        return row is not None

    def list_products(
        self,
        limit: int = 50,
        offset: int = 0,
        platform: Optional[str] = None,
        data_source: Optional[str] = None,
    ) -> list[Product]:
        clauses: list[str] = []
        params: list[Any] = []
        if platform:
            clauses.append("platform = ?")
            params.append(platform)
        if data_source:
            clauses.append("data_source = ?")
            params.append(data_source)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        return self._fetch_products(
            f"SELECT * FROM products {where} ORDER BY collected_at DESC, id DESC LIMIT ? OFFSET ?",
            [*params, limit, offset],
        )

    def search_products(self, query: str, limit: int = 50) -> list[Product]:
        like = f"%{query}%"
        return self._fetch_products(
            """
            SELECT * FROM products
            WHERE product_name LIKE ? OR category LIKE ? OR seller LIKE ? OR data_source LIKE ?
            ORDER BY collected_at DESC, id DESC
            LIMIT ?
            """,
            [like, like, like, like, limit],
        )

    def record_collection_run(self, run: CollectionRun) -> CollectionRun:
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO collection_runs (
                    source_name, platform, status, product_count,
                    response_time_ms, error_message, started_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run.source_name,
                    run.platform,
                    run.status,
                    run.product_count,
                    run.response_time_ms,
                    run.error_message,
                    _to_iso(run.started_at),
                ),
            )
            run_id = cursor.lastrowid
        return run.model_copy(update={"id": run_id})

    def list_sources(self) -> list[dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    p.data_source,
                    COUNT(p.id) AS product_count,
                    MAX(p.collected_at) AS last_collected_at,
                    cr.status AS last_status,
                    cr.response_time_ms AS last_response_time_ms,
                    cr.error_message AS last_error_message
                FROM products p
                LEFT JOIN collection_runs cr ON cr.id = (
                    SELECT id FROM collection_runs
                    WHERE source_name = p.data_source
                    ORDER BY started_at DESC, id DESC
                    LIMIT 1
                )
                GROUP BY p.data_source
                ORDER BY p.data_source
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def _fetch_products(self, query: str, params: list[Any]) -> list[Product]:
        with self.connection() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_product(row) for row in rows]

    def _row_to_product(self, row: sqlite3.Row) -> Product:
        return Product(
            id=row["id"],
            product_name=row["product_name"],
            price=row["price"],
            original_price=row["original_price"],
            shipping_fee=row["shipping_fee"],
            currency=row["currency"],
            category=row["category"],
            seller=row["seller"],
            platform=row["platform"],
            product_url=row["product_url"],
            image_url=row["image_url"],
            condition=row["condition"],
            region=row["region"],
            detail_description=row["detail_description"],
            source_url=row["source_url"],
            source_license=row["source_license"],
            source_observed_at=_from_iso(row["source_observed_at"]) if row["source_observed_at"] else None,
            collected_at=_from_iso(row["collected_at"]),
            data_source=row["data_source"],
        )
