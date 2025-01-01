from sqlalchemy.orm import Session
from .models import Product
from .schemas import ProductCreate

class ProductRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_products(self):
        return self.db.query(Product).all()
    
    def get_products_by_id(self, product_id: int):
        return self.db.query(Product).filter(Product.id == product_id).first()
    
    def create_product(self, product: ProductCreate):
        db_producto = Product(**product.model_dump())
        self.db.add(db_producto)
        self.db.commit()
        self.db.refresh(db_producto)
        return db_producto
    
    def delete_product(self, product_id: int):
        product = self.get_products_by_id(product_id)
        if not product:
            return None  # Maneja esto en el endpoint para devolver un 404 o similar
        self.db.delete(product)
        self.db.commit()
        return product