"""Indexa el catálogo completo de productos en ChromaDB.

Uso:
    uv run python -m app.scripts.index_catalog
"""

import structlog

from ..application.catalog_indexing_service import CatalogIndexingService
from ..core.logging_config import configure_logging
from ..infrastructure.db.product_repository import ProductRepository
from ..infrastructure.db.session import SessionLocal
from ..infrastructure.vectorstore.chromadb_adapter import ChromaDBAdapter

logger = structlog.get_logger(component="index_catalog")


def main() -> None:
    configure_logging()
    db = SessionLocal()
    try:
        product_repo = ProductRepository(db)
        vector_store = ChromaDBAdapter()
        service = CatalogIndexingService(product_repo, vector_store)
        count = service.index_all_products()
        logger.info("Catálogo indexado en ChromaDB", indexed_products=count)
    finally:
        db.close()


if __name__ == "__main__":
    main()
