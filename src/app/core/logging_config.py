"""Configuración central de logging estructurado (structlog → JSON).

Se llama una vez por proceso:
- FastAPI: en `app/main.py`, al importar la app.
- Worker de Celery: en `app/infrastructure/tasks/celery_app.py`, vía la señal
  `worker_process_init` (web y worker corren en procesos separados).

Cada línea de log es un objeto JSON con, al menos, `timestamp` (ISO 8601),
`level` y `event` (mensaje). Cada módulo agrega un campo `component` al crear su
logger, p. ej. `structlog.get_logger(component="cache")`, para poder filtrar por
origen en producción.
"""

import logging
import sys

import structlog


def configure_logging() -> None:
    """Configura structlog para emitir una línea JSON por evento.

    Es idempotente: se puede llamar más de una vez sin efectos secundarios.

    Usamos `WriteLoggerFactory` (escribe directo a stdout) en lugar de la integración
    con `logging` estándar: al no pasar por `logging`, el traceback de una excepción se
    incluye UNA sola vez (dentro del JSON, vía `format_exc_info`) en vez de duplicarse
    (una en el JSON y otra que imprime `logging` por su cuenta con `exc_info`).
    """
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(ensure_ascii=False),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.WriteLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )
