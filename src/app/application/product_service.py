from app.domain.ports.product_repository_port import ProductRepositoryPort
from app.api.schemas.product_schemas import ProductCreate
from app.core.exceptions import NotFoundError


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

    def search_products(self, query: str):
        return self.repo.search_products(query=query)

    def calculate_price(self, product_id: int, cantidad: int, descuento_pct: float = 0):
        product = self.repo.get_products_by_id(product_id=product_id)
        if not product:
            raise NotFoundError(f"Producto con id {product_id} no encontrado")

        subtotal = product.price * cantidad
        descuento = subtotal * (descuento_pct / 100)
        total = subtotal - descuento

        return {
            "product_id": product.id,
            "product_name": product.name,
            "unit_price": product.price,
            "cantidad": cantidad,
            "descuento_pct": descuento_pct,
            "subtotal": subtotal,
            "descuento": descuento,
            "total": total,
        }