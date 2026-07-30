import os

from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI

from ...application.product_service import ProductService
from .product_tools import build_catalog_tools

SYSTEM_PROMPT = """Sos el asistente de Catálogo y Ventas de una tienda online.
Tenés herramientas para buscar productos, consultar stock y calcular precios con
descuento. Usá siempre las herramientas disponibles para responder con datos reales
en lugar de inventar información. Respondé en español, de forma breve y clara."""


def build_catalog_agent(product_service: ProductService, api_key: str | None = None):
    """Construye un agente de LangChain con las tools de catálogo registradas.

    Se crea por request porque las tools quedan atadas al ProductService (y por lo
    tanto a la sesión de base de datos) de esa request.
    """
    llm = ChatGoogleGenerativeAI(
        model="gemini-3.5-flash-lite",
        google_api_key=api_key or os.getenv("GEMINI_API_KEY"),
    )
    tools = build_catalog_tools(product_service)
    return create_agent(model=llm, tools=tools, system_prompt=SYSTEM_PROMPT)


def run_catalog_agent(product_service: ProductService, message: str, api_key: str | None = None) -> str:
    agent = build_catalog_agent(product_service, api_key=api_key)
    result = agent.invoke({"messages": [{"role": "user", "content": message}]})
    final_message = result["messages"][-1]
    return _extract_text(final_message.content)


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
