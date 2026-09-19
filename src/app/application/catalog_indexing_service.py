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

    def _build_document(self, product) -> tuple[str, str, dict]:
        """Construye (doc_id, texto_a_embedear, metadata) para un producto.

        Lógica compartida por el indexado completo y el indexado de un solo
        producto: misma concatenación (nombre + descripción) y mismo formato de
        metadata (product_id + nombre) para que ambos caminos sean consistentes.
        """
        doc_id = str(product.id)
        text = f"{product.name}. {product.description}"
        metadata = {"product_id": product.id, "name": product.name}
        return doc_id, text, metadata

    def index_all_products(self) -> int:
        products = self.product_repo.get_products()
        if not products:
            return 0

        documents = [self._build_document(p) for p in products]
        self.vector_store.index_documents(
            ids=[doc[0] for doc in documents],
            texts=[doc[1] for doc in documents],
            metadatas=[doc[2] for doc in documents],
        )
        return len(products)

    def index_product(self, product_id: int) -> bool:
        """Indexa (o re-indexa) un único producto por su id.

        Devuelve True si el producto existe y fue indexado; False si no existe.
        Se usa desde los endpoints de create/update para mantener el índice
        sincronizado sin necesidad de reindexar todo el catálogo.
        """
        product = self.product_repo.get_products_by_id(product_id)
        if product is None:
            return False

        doc_id, text, metadata = self._build_document(product)
        self.vector_store.index_documents(ids=[doc_id], texts=[text], metadatas=[metadata])
        return True
