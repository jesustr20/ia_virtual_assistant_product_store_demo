import json
import os

import structlog
from dotenv import load_dotenv
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.infrastructure.llm.gemini_adapter import GeminiService
from app.infrastructure.llm.catalog_agent import run_catalog_agent, stream_catalog_agent
from app.infrastructure.db.session import get_db
from app.infrastructure.db.product_repository import ProductRepository
from app.infrastructure.memory.in_memory_conversation_memory import get_conversation_memory
from app.infrastructure.vectorstore.chromadb_adapter import get_vector_store
from app.infrastructure.cache.redis_cache_adapter import get_cache
from app.application.product_service import ProductService
from app.domain.ports.conversation_memory_port import ConversationMemoryPort
from app.domain.ports.vector_store_port import VectorStorePort
from app.domain.ports.cache_port import CachePort, build_cache_key
from app.domain.ports.rate_limiter_port import RateLimiterPort
from app.infrastructure.rate_limiting.redis_rate_limiter import get_rate_limiter
from app.api.schemas.ai_schemas import AskAIRequest, CatalogAgentRequest, CatalogAgentResponse
from app.api.dependencies import enforce_prompt_injection_safety, enforce_rate_limit

load_dotenv()

logger = structlog.get_logger(component="catalogo_stream")

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
    rate_limiter: RateLimiterPort = Depends(get_rate_limiter),
):
    enforce_rate_limit(request.session_id, rate_limiter)
    enforce_prompt_injection_safety(request.message, request.session_id)
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


def _sse_chunk(text: str) -> str:
    """Formatea un token de texto como un evento SSE: `data: {"text": ...}\n\n`.

    `ensure_ascii=False` mantiene acentos/ñ legibles en el wire (el stream viaja en
    UTF-8). El `\n\n` final cierra el evento según la especificación SSE.
    """
    return f"data: {json.dumps({'text': text}, ensure_ascii=False)}\n\n"


def _sse_error_chunk(message: str) -> str:
    """Evento SSE con nombre `error` para señalar un fallo a mitad del stream.

    Usa un tipo de evento distinto (`event: error`) en vez de sobrecargar el shape de
    los chunks de texto, para que el cliente pueda distinguir explícitamente un fin
    limpio de un stream que murió a mitad de camino (y no depender del cierre ambiguo
    de la conexión).
    """
    return f"event: error\ndata: {json.dumps({'error': message}, ensure_ascii=False)}\n\n"


@router.post("/catalogo/stream")
def catalogo_stream(
    request: CatalogAgentRequest,
    db: Session = Depends(get_db),
    memory: ConversationMemoryPort = Depends(get_conversation_memory),
    vector_store: VectorStorePort = Depends(get_vector_store),
    rate_limiter: RateLimiterPort = Depends(get_rate_limiter),
):
    """Variante streaming (SSE) de /catalogo. Consumo desde el cliente:

        curl -N -X POST /ai/catalogo/stream \\
          -H 'Content-Type: application/json' \\
          -d '{"message": "...", "session_id": "..."}'

    El servidor responde `Content-Type: text/event-stream` con una secuencia de eventos
    `data: {"text": "<token>"}\\n\\n`; el cliente los concatena para reconstruir la
    respuesta completa. No se envía un evento final de "done": el fin del stream lo marca
    el cierre de la conexión.
    """
    # Rate limiting ANTES de armar el stream: si la sesión excede el límite devolvemos
    # 429 como respuesta JSON normal. No tendría sentido intentar mandar un 429 a mitad
    # de un stream ya iniciado.
    enforce_rate_limit(request.session_id, rate_limiter)
    enforce_prompt_injection_safety(request.message, request.session_id)

    # El stream NO usa cache (issue #11): un hit de cache es un string completo, y
    # emitirlo "de golpe" como un único chunk no aporta la mejora de latencia percibida
    # que es la razón de ser del streaming. Tampoco ensuciamos la cache de /catalogo, que
    # sigue intacta para el endpoint no-streaming.
    history = memory.get_history(request.session_id)
    product_service = ProductService(ProductRepository(db))

    def generate():
        parts: list[str] = []
        try:
            for chunk in stream_catalog_agent(
                product_service, vector_store, request.message, history=history
            ):
                parts.append(chunk)
                yield _sse_chunk(chunk)
        except Exception:
            logger.exception(
                "Error generando respuesta streaming", session_id=request.session_id
            )
            # Señal de error explícita para el cliente: si no, el stream moriría en
            # silencio y el cliente no sabría distinguir un fin limpio de un fallo.
            yield _sse_error_chunk(
                "Se produjo un error generando la respuesta. Intentá de nuevo."
            )
            # NO registramos el turno en memoria: una respuesta truncada a mitad de
            # frase no debe quedar como contexto (issue #8). Si el cliente reintenta,
            # el reintento parte sin un turno fallido "fantasma" en el historial.
            return

        # Al completar el stream (sin errores), persistimos la respuesta completa en
        # memoria (issue #8), igual que el endpoint no-streaming.
        memory.add_interaction(request.session_id, request.message, "".join(parts))

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )