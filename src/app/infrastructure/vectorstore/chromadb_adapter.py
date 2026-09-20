import os
import threading

import chromadb
from chromadb.api import ClientAPI
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from ...domain.entities.vector_document import VectorSearchResult
from ...domain.ports.vector_store_port import VectorStorePort

load_dotenv()

DEFAULT_COLLECTION_NAME = "products"
DEFAULT_EMBEDDING_MODEL = "models/gemini-embedding-001"
DEFAULT_CHROMA_HOST = "localhost"
DEFAULT_CHROMA_PORT = 8000


class ChromaDBAdapter(VectorStorePort):
    """Implementación de VectorStorePort usando ChromaDB en modo cliente/servidor.

    Se conecta a un servidor de ChromaDB (imagen oficial `chromadb/chroma`) vía
    `HttpClient`, en vez de usar `PersistentClient` embebido en disco. Al haber un
    servidor que maneja la concurrencia, ya no hace falta el workaround de abrir y
    cerrar un cliente fresh por operación (`_open_collection` del issue #12): el
    cliente HTTP se crea una vez y se reutiliza.

    Los embeddings se generan con GoogleGenerativeAIEmbeddings (mismo proveedor
    LLM que el resto del proyecto) — nunca con un modelo local.
    """

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        collection_name: str = DEFAULT_COLLECTION_NAME,
        api_key: str | None = None,
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
    ):
        self._host = host or os.getenv("CHROMA_HOST", DEFAULT_CHROMA_HOST)
        self._port = port or int(os.getenv("CHROMA_PORT", str(DEFAULT_CHROMA_PORT)))
        self._collection_name = collection_name
        self._embeddings = GoogleGenerativeAIEmbeddings(
            model=embedding_model,
            google_api_key=api_key or os.getenv("GEMINI_API_KEY"),
        )
        # El cliente se crea LAZY en `_get_client()`: `chromadb.HttpClient.__init__`
        # hace `get_user_identity()` (un HTTP inmediato), así que NO lo construimos acá
        # para que importar el módulo no exija un servidor de Chroma corriendo.
        self._client: ClientAPI | None = None
        self._client_lock = threading.Lock()

    def _get_client(self) -> ClientAPI:
        """Devuelve el HttpClient, creándolo la primera vez que se necesita.

        Doble chequeo bajo lock: solo se construye UNA vez. Sin el lock, dos threads
        que llegan a la vez al primer uso crearían cada uno su propio `HttpClient`
        (cada uno hace su `get_user_identity()` HTTP), y el perdedor quedaría
        huérfano — su `System`/httpx pool nunca se liberaría (`chromadb` no tiene
        `__del__`, solo `close()`). El lock evita esa doble construcción y esa fuga.
        """
        if self._client is None:
            with self._client_lock:
                if self._client is None:
                    self._client = chromadb.HttpClient(host=self._host, port=self._port)
        return self._client

    def _get_collection(self):
        return self._get_client().get_or_create_collection(name=self._collection_name)

    def index_documents(self, ids: list[str], texts: list[str], metadatas: list[dict]) -> None:
        if not ids:
            return
        vectors = self._embeddings.embed_documents(texts)
        self._get_collection().upsert(
            ids=ids, embeddings=vectors, documents=texts, metadatas=metadatas
        )

    def delete_document(self, doc_id: str) -> None:
        self._get_collection().delete(ids=[doc_id])

    def search(self, query: str, k: int = 5) -> list[VectorSearchResult]:
        collection = self._get_collection()
        count = collection.count()
        if count == 0:
            return []

        query_vector = self._embeddings.embed_query(query)
        results = collection.query(
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


# Instancia única a nivel de módulo (mismo patrón que `conversation_memory`): se
# reutiliza el cliente HTTP y el cliente de embeddings (stateless) por proceso.
vector_store = ChromaDBAdapter()


def get_vector_store() -> VectorStorePort:
    return vector_store
