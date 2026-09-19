from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.schemas.product_schemas import ProductCreate, ProductResponse
from app.core.exceptions import NotFoundError
from app.infrastructure.db.product_repository import ProductRepository
from app.infrastructure.db.session import get_db
from app.infrastructure.tasks.catalog_tasks import reindex_product, remove_product_from_index

from ..dependencies import get_current_user

router = APIRouter()


@router.post("/products", response_model=ProductResponse)
def create_product(
    product: ProductCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    product_repo = ProductRepository(db)
    new_product = product_repo.create_product(product)
    # El reindexado se encola en Celery (background) en vez de correr inline: el request
    # responde inmediato, sin esperar la llamada a la API de embeddings.
    reindex_product.delay(new_product.id)
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
):
    product_repo = ProductRepository(db)
    updated_product = product_repo.update_product(product_id, product)
    if not updated_product:
        raise NotFoundError(f"Producto con id {product_id} no encontrado")
    reindex_product.delay(product_id)
    return updated_product


@router.delete("/products/{product_id}")
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    product_repo = ProductRepository(db)
    product = product_repo.delete_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    remove_product_from_index.delay(product_id)
    return {"detail": f"Product '{product.name}' deleted successfully"}
