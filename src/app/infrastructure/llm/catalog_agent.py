import os
from collections.abc import Iterator

from langchain.agents import create_agent
from langchain_core.messages import AIMessageChunk
from langchain_google_genai import ChatGoogleGenerativeAI

from ...application.product_service import ProductService
from ...core.security.agent_capabilities import select_allowed_tools
from ...domain.entities.conversation_message import ConversationMessage
from ...domain.ports.vector_store_port import VectorStorePort
from .product_tools import build_catalog_tools
from .tracing import GEMINI_FLASH_LITE, traced_llm_call

SYSTEM_PROMPT = """Sos el asistente de Catálogo y Ventas de una tienda online.
Podés: buscar productos, consultar stock y calcular precios con descuento (solo con tus herramientas).
No podés: crear, cancelar ni confirmar pedidos, procesar pagos, hacer reembolsos ni modificar órdenes — no tenés herramientas para eso y esa funcionalidad no existe. Si el usuario lo pide, decile que no podés hacerlo.
Usá siempre tus herramientas para responder con datos reales; nunca inventes ni confirmes una acción que no hayas ejecutado. Respondé en español, de forma breve y clara."""


def build_catalog_agent(
    product_service: ProductService,
    vector_store: VectorStorePort,
    api_key: str | None = None,
):
    """Construye un agente de LangChain con las tools de catálogo registradas.

    Se crea por request porque las tools quedan atadas al ProductService (y por lo
    tanto a la sesión de base de datos) de esa request.

    El conjunto de tools NO se hardcodea acá: se deriva del registro de capacidades
    (`core/security/agent_capabilities.py`, issue #23). `select_allowed_tools` filtra
    las tools disponibles y deja pasar solo las registradas para "catalogo", de modo
    que una tool nueva no registrada jamás llega al agente.
    """
    llm = ChatGoogleGenerativeAI(
        model=GEMINI_FLASH_LITE,
        google_api_key=api_key or os.getenv("GEMINI_API_KEY"),
    )
    available_tools = build_catalog_tools(product_service, vector_store)
    tools = select_allowed_tools("catalogo", available_tools)
    return create_agent(model=llm, tools=tools, system_prompt=SYSTEM_PROMPT)


def run_catalog_agent(
    product_service: ProductService,
    vector_store: VectorStorePort,
    message: str,
    history: list[ConversationMessage] | None = None,
    api_key: str | None = None,
) -> str:
    """Ejecuta el agente de Catálogo con el historial de la sesión como contexto previo.

    `history` son los turnos anteriores de la misma sesión (ver `ConversationMemoryPort`),
    en orden cronológico. Se anteponen al mensaje nuevo para que el agente pueda resolver
    referencias como "esas" o "ese producto" a partir de lo hablado antes.
    """
    agent = build_catalog_agent(product_service, vector_store, api_key=api_key)
    with traced_llm_call(GEMINI_FLASH_LITE, "catalog_agent.invoke") as handler:
        result = agent.invoke(
            {"messages": _build_messages(history, message)},
            config={"callbacks": [handler]},
        )
    final_message = result["messages"][-1]
    return _extract_text(final_message.content)


def stream_catalog_agent(
    product_service: ProductService,
    vector_store: VectorStorePort,
    message: str,
    history: list[ConversationMessage] | None = None,
    api_key: str | None = None,
) -> Iterator[str]:
    """Variante streaming de `run_catalog_agent`: devuelve un generador de tokens.

    Usa `stream_mode="messages"` de LangGraph, que emite token por token (el modelo es
    `ChatGoogleGenerativeAI`, que soporta streaming nativo). Solo se emiten los tokens
    del mensaje final del asistente: se descartan los chunks de tool-calls (contenido
    vacío o bloques `tool_use`) y los resultados de las tools (`ToolMessageChunk`), que
    no deben llegar al cliente.

    El caller debe consumir el generador completo y, al final, persistir el texto
    acumulado (ver `catalogo_stream` en `api/routes/ai_routes.py`).
    """
    agent = build_catalog_agent(product_service, vector_store, api_key=api_key)
    with traced_llm_call(GEMINI_FLASH_LITE, "catalog_agent.stream") as handler:
        for chunk, _metadata in agent.stream(
            {"messages": _build_messages(history, message)},
            stream_mode="messages",
            config={"callbacks": [handler]},
        ):
            if isinstance(chunk, AIMessageChunk):
                text = _extract_text(chunk.content)
                if text:
                    yield text


def _build_messages(
    history: list[ConversationMessage] | None, message: str
) -> list[dict]:
    """Arma la lista de mensajes para el agente: historial + mensaje nuevo del usuario."""
    messages = [{"role": m.role, "content": m.content} for m in (history or [])]
    messages.append({"role": "user", "content": message})
    return messages


def _extract_text(content) -> str:
    """Normaliza el content de la respuesta del LLM a un string plano.

    Algunos proveedores (ej. Gemini) devuelven el content como una lista de
    bloques `{"type": "text", "text": "..."}` en lugar de un string simple.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            block.get("text", "") for block in content if isinstance(block, dict)
        )
    return str(content)
