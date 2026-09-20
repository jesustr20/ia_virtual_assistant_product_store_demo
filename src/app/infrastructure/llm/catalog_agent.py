import os
from collections.abc import Iterator

from langchain.agents import create_agent
from langchain_core.messages import AIMessageChunk
from langchain_google_genai import ChatGoogleGenerativeAI

from ...application.product_service import ProductService
from ...domain.entities.conversation_message import ConversationMessage
from ...domain.ports.vector_store_port import VectorStorePort
from .product_tools import build_catalog_tools

SYSTEM_PROMPT = """Sos el asistente de Catálogo y Ventas de una tienda online.
Tenés herramientas para buscar productos, consultar stock y calcular precios con
descuento. Usá siempre las herramientas disponibles para responder con datos reales
en lugar de inventar información. Respondé en español, de forma breve y clara."""


def build_catalog_agent(
    product_service: ProductService,
    vector_store: VectorStorePort,
    api_key: str | None = None,
):
    """Construye un agente de LangChain con las tools de catálogo registradas.

    Se crea por request porque las tools quedan atadas al ProductService (y por lo
    tanto a la sesión de base de datos) de esa request.
    """
    llm = ChatGoogleGenerativeAI(
        model="gemini-3.5-flash-lite",
        google_api_key=api_key or os.getenv("GEMINI_API_KEY"),
    )
    tools = build_catalog_tools(product_service, vector_store)
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
    result = agent.invoke({"messages": _build_messages(history, message)})
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
    for chunk, _metadata in agent.stream(
        {"messages": _build_messages(history, message)}, stream_mode="messages"
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
