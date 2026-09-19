from ..domain.ports.product_repository_port import ProductRepositoryPort
from ..domain.ports.vector_store_port import VectorStorePort


class CatalogIndexingService:
    """Indexa el catálogo de productos existente en el vector store para RAG.

    Concatena nombre + descripción como texto a embeddear, y guarda el id del
    producto en la metadata para poder recuperarlo después de una búsqueda
    semántica.
    """

    def __init__(self, product_repo: ProductRepositoryPort, vector_store: VectorStorePort):
        self.product_repo = product_repo
        self.vector_store = vector_store

    def index_all_products(self) -> int:
        products = self.product_repo.get_products()
        if not products:
            return 0

        ids = [str(p.id) for p in products]
        texts = [f"{p.name}. {p.description}" for p in products]
        metadatas = [{"product_id": p.id, "name": p.name} for p in products]

        self.vector_store.index_documents(ids=ids, texts=texts, metadatas=metadatas)
        return len(products)
