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
        self._client = chromadb.PersistentClient(path=self._persist_directory)
        self._collection = self._client.get_or_create_collection(name=collection_name)
        self._embeddings = GoogleGenerativeAIEmbeddings(
            model=embedding_model,
            google_api_key=api_key or os.getenv("GEMINI_API_KEY"),
        )

    def index_documents(self, ids: list[str], texts: list[str], metadatas: list[dict]) -> None:
        if not ids:
            return
        vectors = self._embeddings.embed_documents(texts)
        self._collection.upsert(ids=ids, embeddings=vectors, documents=texts, metadatas=metadatas)

    def delete_document(self, doc_id: str) -> None:
        self._collection.delete(ids=[doc_id])

    def search(self, query: str, k: int = 5) -> list[VectorSearchResult]:
        count = self._collection.count()
        if count == 0:
            return []

        query_vector = self._embeddings.embed_query(query)
        results = self._collection.query(
            query_embeddings=[query_vector], n_results=min(k, count)
        )

        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances") or [[]]
        distances = distances[0] if distances else [None] * len(ids)

        return [
            VectorSearchResult(id=doc_id, text=text, metadata=metadata or {}, score=distance)
            for doc_id, text, metadata, distance in zip(ids, documents, metadatas, distances)
        ]


# Instancia única a nivel de módulo: crear un ChromaDBAdapter por request implicaría
# abrir un nuevo PersistentClient de ChromaDB y un nuevo cliente de embeddings en cada
# request, algo costoso e innecesario. Igual que `conversation_memory` en
# `in_memory_conversation_memory.py`, se crea una sola vez por proceso y se expone vía
# `get_vector_store` para inyectarla con `Depends`.
vector_store = ChromaDBAdapter()


def get_vector_store() -> VectorStorePort:
    return vector_store
