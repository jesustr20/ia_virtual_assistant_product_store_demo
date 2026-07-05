from app.domain.ports.product_repository_port import ProductRepositoryPort
from app.api.schemas.product_schemas import ProductCreate


class ProductService:
    def __init__(self, repo: ProductRepositoryPort):
        self.repo = repo

    def get_products(self):
        return self.repo.get_products()

    def get_product_by_id(self, product_id: int):
        return self.repo.get_products_by_id(product_id=product_id)

    def create_product(self, product: ProductCreate):
        return self.repo.create_product(product)
    
    def update_product(self, product_id: int, product: ProductCreate):
        return self.repo.update_product(product_id=product_id, product=product)
    
    def delete_product(self, product_id: int):
        return self.repo.delete_product(product_id=product_id)