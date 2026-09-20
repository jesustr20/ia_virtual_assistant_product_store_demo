"""Trazado de llamadas a LLM: latencia, tokens consumidos y costo estimado (issue #16).

Envolvemos cada llamada al modelo con un context manager que:
1. mide la latencia,
2. captura los tokens (de `usage_metadata`, que LangChain expone en el `AIMessage`
   de cada respuesta, vía un callback `on_llm_end` — no contamos tokens a mano),
3. loguea una línea structlog por llamada con `model`, `kind`, `latency_ms`,
   `input_tokens`, `output_tokens`, `total_tokens` y `estimated_cost_usd`.

Es puramente aditivo: no cambia ningún comportamiento ni respuesta.
"""

import time
from collections.abc import Iterator
from contextlib import contextmanager

import structlog
from langchain_core.callbacks import BaseCallbackHandler

logger = structlog.get_logger(component="llm_tracing")

# Nombre del modelo usado por el router y el agente de catálogo (mismo string que se
# pasa a `ChatGoogleGenerativeAI(model=...)`).
GEMINI_FLASH_LITE = "gemini-3.5-flash-lite"

# Precio por modelo, en USD por MILLÓN de tokens (input / output). Fuente: página de
# precios de Google (Gemini 3.5 Flash-Lite, on-demand, región global). Hay que actualizar
# esta tabla a mano si Google cambia los precios — no hay API de precios en vivo (overkill
# para este scope).
MODEL_PRICING_USD: dict[str, dict[str, float]] = {
    GEMINI_FLASH_LITE: {"input": 0.30, "output": 2.50},
}


class _UsageCaptureHandler(BaseCallbackHandler):
    """Acumula `usage_metadata` de TODAS las llamadas al LLM de una invocación.

    Un agente con tool-calling puede invocar al modelo más de una vez (una para decidir
    la tool, otra para la respuesta final); sumar todos los `on_llm_end` da el total real
    de tokens de la llamada, en vez de solo la última ronda.
    """

    def __init__(self) -> None:
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0

    def on_llm_end(self, response, **kwargs) -> None:
        for generation_list in response.generations:
            for generation in generation_list:
                message = getattr(generation, "message", generation)
                usage = getattr(message, "usage_metadata", None)
                if not usage:
                    continue
                self.input_tokens += usage.get("input_tokens", 0)
                self.output_tokens += usage.get("output_tokens", 0)
                self.total_tokens += usage.get("total_tokens", 0)


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    """Costo estimado de una llamada según la tabla de precios (0 si el modelo no está)."""
    pricing = MODEL_PRICING_USD.get(model)
    if pricing is None:
        return 0.0
    return (
        input_tokens / 1_000_000 * pricing["input"]
        + output_tokens / 1_000_000 * pricing["output"]
    )


@contextmanager
def traced_llm_call(model: str, kind: str) -> Iterator[_UsageCaptureHandler]:
    """Context manager que mide latencia, captura tokens y loguea al salir.

    El caller recibe el handler y debe pasarlo al modelo vía
    `config={"callbacks": [handler]}` para que LangChain dispare `on_llm_end`.
    """
    handler = _UsageCaptureHandler()
    start = time.perf_counter()
    try:
        yield handler
    finally:
        latency_ms = (time.perf_counter() - start) * 1000
        _log_trace(model, kind, latency_ms, handler.input_tokens, handler.output_tokens)


def _log_trace(
    model: str,
    kind: str,
    latency_ms: float,
    input_tokens: int,
    output_tokens: int,
) -> None:
    logger.info(
        "llm_call",
        model=model,
        kind=kind,
        latency_ms=round(latency_ms, 2),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        estimated_cost_usd=round(estimate_cost_usd(model, input_tokens, output_tokens), 8),
    )
