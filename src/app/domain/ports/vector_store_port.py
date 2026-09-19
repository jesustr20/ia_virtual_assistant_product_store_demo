from abc import ABC, abstractmethod

from ..entities.vector_document import VectorSearchResult


class VectorStorePort(ABC):
    """Puerto para indexar documentos y buscarlos por similitud semántica.

    Agnóstico del motor de vectores concreto (ChromaDB, Pinecone, etc.) — las
    implementaciones concretas viven en `infrastructure/vectorstore/`.
    """

    @abstractmethod
    def index_documents(self, ids: list[str], texts: list[str], metadatas: list[dict]) -> None:
        """Indexa un lote de documentos (si un id ya existe, lo reemplaza)."""

    @abstractmethod
    def search(self, query: str, k: int = 5) -> list[VectorSearchResult]:
        """Devuelve los `k` documentos más similares semánticamente a `query`."""
