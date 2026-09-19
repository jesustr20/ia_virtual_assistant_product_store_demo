from ...application.catalog_indexing_service import CatalogIndexingService
from ..db.product_repository import ProductRepository
from ..db.session import SessionLocal
from ..vectorstore.chromadb_adapter import ChromaDBAdapter
from .celery_app import celery_app


@celery_app.task(name="catalog.reindex_product")
def reindex_product(product_id: int) -> None:
    """Re-indexa un producto en ChromaDB (creado o actualizado).

    El worker de Celery corre en un proceso aparte de FastAPI, así que acá construimos
    nuestra propia sesión de DB (SessionLocal, igual que get_db pero sin contexto de
    request) y una instancia fresca de ChromaDBAdapter (el singleton del proceso web no
    se comparte entre procesos).
    """
    db = SessionLocal()
    try:
        product_repo = ProductRepository(db)
        vector_store = ChromaDBAdapter()
        CatalogIndexingService(product_repo, vector_store).index_product(product_id)
    finally:
        db.close()


@celery_app.task(name="catalog.remove_product_from_index")
def remove_product_from_index(product_id: int) -> None:
    """Elimina un producto del índice de ChromaDB (producto eliminado)."""
    vector_store = ChromaDBAdapter()
    vector_store.delete_document(str(product_id))
