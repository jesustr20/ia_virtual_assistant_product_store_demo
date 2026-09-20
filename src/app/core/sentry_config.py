"""Inicialización de Sentry para error tracking (issue #17).

Se llama una vez por proceso, igual que `configure_logging` (issue #15):
- FastAPI: en `app/main.py`, al importar la app.
- Worker de Celery: en `app/infrastructure/tasks/celery_app.py`, vía la señal
  `worker_process_init` (web y worker corren en procesos separados).

Si `SENTRY_DSN` no está definida, `init_sentry` no hace nada: la app sigue
funcionando normalmente sin Sentry (no es un requisito para correr el proyecto).
"""

import os

import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration

from .exceptions import AppException


def before_send(event, hint):
    """Descarta los errores de negocio (`AppException` y subclases).

    Son resultados esperados (producto no encontrado, credenciales inválidas, rate
    limit, etc.), no bugs: no deben llegar a Sentry. Solo reportamos excepciones
    verdaderamente no manejadas (las que captura `generic_exception_handler`).
    """
    exc_info = hint.get("exc_info")
    if exc_info is not None:
        exc_type, exc_value, _tb = exc_info
        exc = exc_value if exc_value is not None else exc_type
        if isinstance(exc, AppException):
            return None
    return event


def init_sentry(transport=None) -> None:
    """Inicializa el SDK de Sentry si `SENTRY_DSN` está definida.

    `transport` solo se usa para tests (inyectar un transport que captura eventos en
    memoria en vez de enviarlos por red).
    """
    dsn = os.getenv("SENTRY_DSN")
    if not dsn:
        return

    sentry_sdk.init(
        dsn=dsn,
        integrations=[FastApiIntegration(), CeleryIntegration()],
        # Por defecto ya es False, pero lo dejamos explícito para que quede claro que
        # NO capturamos datos personales (bodies, headers, cookies) en los eventos.
        send_default_pii=False,
        before_send=before_send,
        # Solo errores (no performance tracing): issue #17 es error tracking.
        traces_sample_rate=0.0,
        transport=transport,
    )
