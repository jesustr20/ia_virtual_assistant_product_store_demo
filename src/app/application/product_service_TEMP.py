from sqlalchemy.orm import Session
from ..repositories import ProductRepository
from ..schemas import ProductCreate

class ProductoService:
    def __init__(self, db: Session):
        self.repo = ProductRepository(db)        

    def list_products(self):
        return self.repo.get_products()

    def get_product(self, product_id: int):
        return self.repo.get_products_by_id(product_id)

    def create_product(self, product: ProductCreate):
        return self.repo.create_product(product)