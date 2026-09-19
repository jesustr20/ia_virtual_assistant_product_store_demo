from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.infrastructure.llm.gemini_adapter import GeminiService
from app.infrastructure.llm.catalog_agent import run_catalog_agent
from app.infrastructure.db.session import get_db
from app.infrastructure.db.product_repository import ProductRepository
from app.infrastructure.memory.in_memory_conversation_memory import get_conversation_memory
from app.infrastructure.vectorstore.chromadb_adapter import get_vector_store
from app.infrastructure.cache.redis_cache_adapter import get_cache
from app.application.product_service import ProductService
from app.domain.ports.conversation_memory_port import ConversationMemoryPort
from app.domain.ports.vector_store_port import VectorStorePort
from app.domain.ports.cache_port import CachePort, build_cache_key
from app.api.schemas.ai_schemas import AskAIRequest, CatalogAgentRequest, CatalogAgentResponse
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

# TTL de la cache del agente de catálogo. La respuesta puede incluir precio/stock,
# que cambian cuando se crea/edita/elimina un producto (issue #10) — y esas
# operaciones NO invalidan esta cache. 5 minutos es un compromiso razonable: absorbe
# preguntas repetidas (el mayor ahorro de costo/latencia) sin servir datos de
# stock/precio obsoletos por demasiado tiempo.
CATALOG_CACHE_AGENT = "catalogo"
CATALOG_CACHE_TTL_SECONDS = 300


@router.post("/ask_ai")
def ask_ai(request: AskAIRequest, db: Session = Depends(get_db)):
    gemini_service = GeminiService(api_key=os.getenv("GEMINI_API_KEY"), product_repo=ProductRepository(db))
    if "producto" in request.question.lower():
        return {"respuesta": gemini_service.respond_with_products(request.question)}
    else:
        return {"respuesta": gemini_service.get_humanlike_response(request.question)}

@router.post("/catalogo", response_model=CatalogAgentResponse)
def catalogo(
    request: CatalogAgentRequest,
    db: Session = Depends(get_db),
    memory: ConversationMemoryPort = Depends(get_conversation_memory),
    vector_store: VectorStorePort = Depends(get_vector_store),
    cache: CachePort = Depends(get_cache),
):
    # Solo cacheamos el PRIMER turno de una sesión (historial vacío). El agente de
    # catálogo resuelve referencias como "esas"/"eso" a partir del historial (issue #8),
    # así que el mismo texto de follow-up ("¿cuánto cuestan esas?") puede significar
    # cosas distintas según lo hablado antes en cada sesión. Si ya hay historial, NO
    # leemos ni escribimos la cache y siempre llamamos al agente con su contexto.
    history = memory.get_history(request.session_id)
    cache_key = build_cache_key(CATALOG_CACHE_AGENT, request.message)
    response = cache.get(cache_key) if not history else None
    if response is None:
        product_service = ProductService(ProductRepository(db))
        response = run_catalog_agent(product_service, vector_store, request.message, history=history)
        if not history:
            cache.set(cache_key, response, CATALOG_CACHE_TTL_SECONDS)
    memory.add_interaction(request.session_id, request.message, response)
    return CatalogAgentResponse(response=response)