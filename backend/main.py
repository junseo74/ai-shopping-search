import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query

try:
    from .collectors import (
        ApprovedHtmlProductCollector,
        BaseCollector,
        EbayBrowseCollector,
        ElevenstProductCollector,
        TestFixtureCollector,
    )
    from .db import ProductRepository
    from .importers import ProductFileImporter
    from .models import CollectionRun, Product
except ImportError:  # Allows `uvicorn main:app` from the backend directory.
    from collectors import (
        ApprovedHtmlProductCollector,
        BaseCollector,
        EbayBrowseCollector,
        ElevenstProductCollector,
        TestFixtureCollector,
    )
    from db import ProductRepository
    from importers import ProductFileImporter
    from models import CollectionRun, Product


def build_collectors() -> dict[str, BaseCollector]:
    collectors: list[BaseCollector] = [
        TestFixtureCollector(),
        EbayBrowseCollector(),
        ElevenstProductCollector(),
        ApprovedHtmlProductCollector(),
    ]
    return {collector.metadata.source_name: collector for collector in collectors}


def is_collector_configured(collector: BaseCollector) -> bool:
    if collector.metadata.source_name == "ebay_browse":
        ebay_collector = collector
        return bool(getattr(ebay_collector, "client_id", None) and getattr(ebay_collector, "client_secret", None))
    if collector.metadata.source_name == "elevenst":
        elevenst_collector = collector
        return bool(getattr(elevenst_collector, "api_key", None))
    if collector.metadata.source_name == "approved_html":
        html_collector = collector
        return bool(getattr(html_collector, "urls", None))
    return True


def summarize_products(products: list[Product], response_time_ms: float) -> dict:
    total = len(products)
    sellers = {product.seller for product in products if product.seller}
    if total == 0:
        return {
            "product_count": 0,
            "seller_count": 0,
            "response_time_ms": round(response_time_ms, 2),
            "missing_price_rate": 0,
            "missing_shipping_fee_rate": 0,
            "missing_product_url_rate": 0,
        }
    return {
        "product_count": total,
        "seller_count": len(sellers),
        "response_time_ms": round(response_time_ms, 2),
        "missing_price_rate": round(sum(product.price is None for product in products) / total, 4),
        "missing_shipping_fee_rate": round(sum(product.shipping_fee is None for product in products) / total, 4),
        "missing_product_url_rate": round(sum(product.product_url is None for product in products) / total, 4),
        "missing_detail_description_rate": round(
            sum(product.detail_description is None for product in products) / total,
            4,
        ),
    }


def create_app(db_path: Optional[str | Path] = None) -> FastAPI:
    app = FastAPI(title="AI Shopping Search API")
    repository = ProductRepository(db_path)
    collectors = build_collectors()

    @app.get("/")
    def home():
        return {
            "message": "AI Shopping Search \uc11c\ubc84 \uc2e4\ud589 \uc131\uacf5",
            "status": "ok",
        }

    @app.get("/products", response_model=list[Product])
    def get_products(
        limit: int = Query(default=50, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
        platform: Optional[str] = None,
        data_source: Optional[str] = None,
    ):
        return repository.list_products(
            limit=limit,
            offset=offset,
            platform=platform,
            data_source=data_source,
        )

    @app.get("/search", response_model=list[Product])
    def search_products(
        q: str = Query(..., min_length=1),
        limit: int = Query(default=50, ge=1, le=200),
    ):
        return repository.search_products(query=q, limit=limit)

    @app.get("/sources")
    def get_sources():
        registered = {
            name: {
                "source_name": collector.metadata.source_name,
                "platform": collector.metadata.platform,
                "requires_api_key": collector.metadata.requires_api_key,
                "enabled": collector.metadata.enabled,
                "configured": is_collector_configured(collector),
                "connected": is_collector_configured(collector),
            }
            for name, collector in collectors.items()
        }
        stored = {source["data_source"]: source for source in repository.list_sources()}
        return [
            {
                **metadata,
                "product_count": stored.get(name, {}).get("product_count", 0),
                "last_collected_at": stored.get(name, {}).get("last_collected_at"),
                "last_status": stored.get(name, {}).get("last_status"),
                "last_response_time_ms": stored.get(name, {}).get("last_response_time_ms"),
                "last_error_message": stored.get(name, {}).get("last_error_message"),
            }
            for name, metadata in registered.items()
        ]

    @app.post("/collect/{source_name}", response_model=CollectionRun)
    def collect_products(
        source_name: str,
        q: Optional[str] = None,
        limit: int = Query(default=50, ge=1, le=200),
    ):
        collector = collectors.get(source_name)
        if not collector:
            raise HTTPException(status_code=404, detail=f"Unknown source: {source_name}")

        started = time.perf_counter()
        try:
            products = collector.collect(query=q, limit=limit)
            repository.add_products(products)
            status = "success"
            error_message = None
        except Exception as exc:
            products = []
            status = "failed"
            error_message = str(exc)

        elapsed_ms = (time.perf_counter() - started) * 1000
        run = CollectionRun(
            source_name=collector.metadata.source_name,
            platform=collector.metadata.platform,
            status=status,
            product_count=len(products),
            response_time_ms=round(elapsed_ms, 2),
            error_message=error_message,
        )
        recorded = repository.record_collection_run(run)
        if status == "failed":
            raise HTTPException(status_code=500, detail=recorded.model_dump())
        return recorded

    @app.post("/collect/{source_name}/benchmark")
    def benchmark_collection(
        source_name: str,
        queries: list[str] = Query(default=["coffee", "laptop", "shirt"]),
        limit: int = Query(default=20, ge=1, le=200),
    ):
        collector = collectors.get(source_name)
        if not collector:
            raise HTTPException(status_code=404, detail=f"Unknown source: {source_name}")

        results = []
        total_products = 0
        all_sellers = set()
        for query in queries:
            started = time.perf_counter()
            try:
                products = collector.collect(query=query, limit=limit)
                repository.add_products(products)
                elapsed_ms = (time.perf_counter() - started) * 1000
                repository.record_collection_run(
                    CollectionRun(
                        source_name=collector.metadata.source_name,
                        platform=collector.metadata.platform,
                        status="success",
                        product_count=len(products),
                        response_time_ms=round(elapsed_ms, 2),
                    )
                )
                summary = summarize_products(products, elapsed_ms)
                total_products += len(products)
                all_sellers.update(product.seller for product in products if product.seller)
                results.append({"query": query, "status": "success", **summary})
            except Exception as exc:
                elapsed_ms = (time.perf_counter() - started) * 1000
                repository.record_collection_run(
                    CollectionRun(
                        source_name=collector.metadata.source_name,
                        platform=collector.metadata.platform,
                        status="failed",
                        product_count=0,
                        response_time_ms=round(elapsed_ms, 2),
                        error_message=str(exc),
                    )
                )
                results.append(
                    {
                        "query": query,
                        "status": "failed",
                        "product_count": 0,
                        "seller_count": 0,
                        "response_time_ms": round(elapsed_ms, 2),
                        "error_message": str(exc),
                    }
                )

        return {
            "source_name": source_name,
            "query_count": len(queries),
            "total_product_count": total_products,
            "total_seller_count": len(all_sellers),
            "results": results,
        }

    @app.post("/import/products")
    def import_products(
        file_path: str,
        data_source: str,
        source_url: Optional[str] = None,
        source_license: Optional[str] = None,
        source_observed_at: Optional[str] = None,
        limit: int = Query(default=20, ge=1, le=10000),
    ):
        started = time.perf_counter()
        try:
            observed_at = datetime.fromisoformat(source_observed_at) if source_observed_at else None
            products = ProductFileImporter().load(
                file_path=file_path,
                data_source=data_source,
                source_url=source_url,
                source_license=source_license,
                source_observed_at=observed_at,
                limit=limit,
            )
            saved = repository.add_products(products)
            status = "success"
            error_message = None
        except Exception as exc:
            saved = []
            status = "failed"
            error_message = str(exc)

        elapsed_ms = (time.perf_counter() - started) * 1000
        run = CollectionRun(
            source_name=data_source,
            platform="shopping_mall",
            status=status,
            product_count=len(saved),
            response_time_ms=round(elapsed_ms, 2),
            error_message=error_message,
        )
        repository.record_collection_run(run)
        if status == "failed":
            raise HTTPException(status_code=500, detail=error_message)
        return {
            "status": status,
            "data_source": data_source,
            "imported_count": len(saved),
            "response_time_ms": round(elapsed_ms, 2),
            "source_url": source_url,
            "source_license": source_license,
            "source_observed_at": source_observed_at,
        }

    return app


app = create_app()
