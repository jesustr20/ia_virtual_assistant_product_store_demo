from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.repositories import ProductRepository
from app.schemas import ProductCreate, ProductResponse

router = APIRouter()

@router.post("/products", response_model=ProductResponse)
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    product_repo = ProductRepository(db)
    new_product = product_repo.create_product(product)
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

@router.delete("/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product_repo = ProductRepository(db)
    product = product_repo.delete_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"detail": f"Product '{product.name}' deleted successfully"}