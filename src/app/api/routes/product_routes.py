import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.schemas.product_schemas import ProductCreate, ProductResponse
from app.application.catalog_indexing_service import CatalogIndexingService
from app.core.exceptions import NotFoundError
from app.domain.ports.vector_store_port import VectorStorePort
from app.infrastructure.db.product_repository import ProductRepository
from app.infrastructure.db.session import get_db
from app.infrastructure.vectorstore.chromadb_adapter import get_vector_store

from ..dependencies import get_current_user

logger = logging.getLogger("app")

router = APIRouter()


# La sincronización del índice vectorial se hace de forma síncrona (dentro del request)
# y *best-effort*: si falla (p.ej. la API de embeddings no responde), se loguea el error
# pero el request de create/update/delete devuelve éxito igual. Postgres ya persistió el
# producto y es la fuente de verdad; el índice es una cache derivada que se puede
# reconstruir en cualquier momento con `uv run python -m app.scripts.index_catalog`.
# Por eso NO propagamos la excepción ni la convertimos en una AppException (que está
# pensada para errores de negocio que sí debe ver el cliente). Se usa el mismo logger
# "app" que core/error_handlers.py.
def _index_product_best_effort(
    product_repo: ProductRepository,
    vector_store: VectorStorePort,
    product_id: int,
) -> None:
    try:
        CatalogIndexingService(product_repo, vector_store).index_product(product_id)
    except Exception:
        logger.exception("No se pudo indexar el producto %s en ChromaDB", product_id)


def _delete_product_from_index_best_effort(
    vector_store: VectorStorePort,
    product_id: int,
) -> None:
    try:
        vector_store.delete_document(str(product_id))
    except Exception:
        logger.exception("No se pudo eliminar el producto %s de ChromaDB", product_id)


@router.post("/products", response_model=ProductResponse)
def create_product(
    product: ProductCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
    vector_store: VectorStorePort = Depends(get_vector_store),
):
    product_repo = ProductRepository(db)
    new_product = product_repo.create_product(product)
    _index_product_best_effort(product_repo, vector_store, new_product.id)
    return new_product


@router.get("/products/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product_repo = ProductRepository(db)
    product = product_repo.get_products_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.get("/products", response_model=list[ProductResponse])
def list_products(db: Session = Depends(get_db)):
    product_repo = ProductRepository(db)
    products = product_repo.get_products()
    return products


@router.put("/products/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    product: ProductCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
    vector_store: VectorStorePort = Depends(get_vector_store),
):
    product_repo = ProductRepository(db)
    updated_product = product_repo.update_product(product_id, product)
    if not updated_product:
        raise NotFoundError(f"Producto con id {product_id} no encontrado")
    _index_product_best_effort(product_repo, vector_store, product_id)
    return updated_product


@router.delete("/products/{product_id}")
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
    vector_store: VectorStorePort = Depends(get_vector_store),
):
    product_repo = ProductRepository(db)
    product = product_repo.delete_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    _delete_product_from_index_best_effort(vector_store, product_id)
    return {"detail": f"Product '{product.name}' deleted successfully"}
