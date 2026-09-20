import os
from langchain_google_genai import ChatGoogleGenerativeAI
from ...domain.ports.router_port import RouterPort
from ...domain.entities.route_decision import RouteDecision
from .tracing import GEMINI_FLASH_LITE, traced_llm_call

SYSTEM_PROMPT = """Sos un clasificador de intenciones para un asistente de ventas de una tienda online.
Analizá el mensaje del usuario y clasificalo en UNA sola categoría:

- CATALOGO: preguntas sobre productos, stock, precios, características
- VENTAS: quiere comprar, confirmar una compra, aplicar descuentos
- SOPORTE: quejas, devoluciones, estado de pedidos, problemas

Respondé solo con la categoría correcta."""


class GeminiRouterAdapter(RouterPort):
    def __init__(self, api_key: str | None = None):
        self.llm = ChatGoogleGenerativeAI(
            model=GEMINI_FLASH_LITE,
            google_api_key=api_key or os.getenv("GEMINI_API_KEY"),
        )
        self.structured_llm = self.llm.with_structured_output(RouteDecision)

    def classify(self, message: str) -> RouteDecision:
        with traced_llm_call(GEMINI_FLASH_LITE, "router.classify") as handler:
            return self.structured_llm.invoke(
                [
                    ("system", SYSTEM_PROMPT),
                    ("human", message),
                ],
                config={"callbacks": [handler]},
            )