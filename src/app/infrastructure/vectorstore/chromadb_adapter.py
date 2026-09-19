import os
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from ...domain.entities.vector_document import VectorSearchResult
from ...domain.ports.vector_store_port import VectorStorePort

load_dotenv()

# Raíz del proyecto (sube desde src/app/infrastructure/vectorstore/ hasta la raíz).
_PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_PERSIST_DIR = str(_PROJECT_ROOT / "chroma_data")
DEFAULT_COLLECTION_NAME = "products"
DEFAULT_EMBEDDING_MODEL = "models/gemini-embedding-001"


class ChromaDBAdapter(VectorStorePort):
    """Implementación de VectorStorePort usando ChromaDB persistido en disco.

    Los embeddings se generan con GoogleGenerativeAIEmbeddings (mismo proveedor
    LLM que el resto del proyecto) — nunca con un modelo local.
    """

    def __init__(
        self,
        persist_directory: str | None = None,
        collection_name: str = DEFAULT_COLLECTION_NAME,
        api_key: str | None = None,
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
    ):
        self._persist_directory = persist_directory or os.getenv(
            "CHROMA_PERSIST_DIR", DEFAULT_PERSIST_DIR
        )
        self._collection_name = collection_name
        self._embeddings = GoogleGenerativeAIEmbeddings(
            model=embedding_model,
            google_api_key=api_key or os.getenv("GEMINI_API_KEY"),
        )

    def _open_collection(self):
        """Abre un cliente/colección FRESCOS de ChromaDB en cada operación.

        ChromaDB en modo local cachea el índice HNSW en memoria y lo persiste a disco
        recién al hacer `close()`. Abrir fresh en cada operación + cerrar al final es lo
        que garantiza que: (1) las escrituras de OTRO proceso (el worker de Celery
        reindexando) se vean en lecturas posteriores, y (2) las escrituras propias queden
        persistidas y visibles para los demás procesos. El cliente de embeddings sí se
        reutiliza (es stateless: la parte cara es la llamada HTTP, no abrir SQLite).

        Devuelve la tupla (client, collection); el caller DEBE llamar `client.close()`.
        """
        client = chromadb.PersistentClient(path=self._persist_directory)
        return client, client.get_or_create_collection(name=self._collection_name)

    def index_documents(self, ids: list[str], texts: list[str], metadatas: list[dict]) -> None:
        if not ids:
            return
        vectors = self._embeddings.embed_documents(texts)
        client, collection = self._open_collection()
        try:
            collection.upsert(
                ids=ids, embeddings=vectors, documents=texts, metadatas=metadatas
            )
        finally:
            client.close()

    def delete_document(self, doc_id: str) -> None:
        client, collection = self._open_collection()
        try:
            collection.delete(ids=[doc_id])
        finally:
            client.close()

    def search(self, query: str, k: int = 5) -> list[VectorSearchResult]:
        client, collection = self._open_collection()
        try:
            count = collection.count()
            if count == 0:
                return []

            query_vector = self._embeddings.embed_query(query)
            results = collection.query(
                query_embeddings=[query_vector], n_results=min(k, count)
            )
        finally:
            client.close()

        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances") or [[]]
        distances = distances[0] if distances else [None] * len(ids)

        return [
            VectorSearchResult(id=doc_id, text=text, metadata=metadata or {}, score=distance)
            for doc_id, text, metadata, distance in zip(ids, documents, metadatas, distances)
        ]


# Instancia única a nivel de módulo (mismo patrón que `conversation_memory`): se reutiliza
# el cliente de embeddings (stateless) por proceso. El cliente de ChromaDB se abre fresh
# en cada operación (ver `_open_collection`) para no servir datos stale entre procesos.
vector_store = ChromaDBAdapter()


def get_vector_store() -> VectorStorePort:
    return vector_store
