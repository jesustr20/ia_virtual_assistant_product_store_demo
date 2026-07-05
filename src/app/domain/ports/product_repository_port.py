from abc import ABC, abstractmethod

class ProductRepositoryPort(ABC):

    @abstractmethod
    def get_products(self):
        pass
    
    @abstractmethod
    def get_products_by_id(self, product_id):
        pass

    @abstractmethod
    def create_product(self, product):
        pass

    @abstractmethod
    def update_product(self, product_id, product):
        pass

    @abstractmethod
    def delete_product(self, product_id):
        pass