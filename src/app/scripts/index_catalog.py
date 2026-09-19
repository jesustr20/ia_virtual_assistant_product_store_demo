"""Indexa el catálogo completo de productos en ChromaDB.

Uso:
    uv run python -m app.scripts.index_catalog
"""

from ..application.catalog_indexing_service import CatalogIndexingService
from ..infrastructure.db.product_repository import ProductRepository
from ..infrastructure.db.session import SessionLocal
from ..infrastructure.vectorstore.chromadb_adapter import ChromaDBAdapter


def main() -> None:
    db = SessionLocal()
    try:
        product_repo = ProductRepository(db)
        vector_store = ChromaDBAdapter()
        service = CatalogIndexingService(product_repo, vector_store)
        count = service.index_all_products()
        print(f"Indexados {count} producto(s) en ChromaDB.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
