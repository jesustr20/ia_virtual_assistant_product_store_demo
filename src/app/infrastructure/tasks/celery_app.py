import os

from celery import Celery
from celery.signals import worker_process_init
from dotenv import load_dotenv

from ...core.logging_config import configure_logging

load_dotenv()

# Broker: reutilizamos el MISMO Redis de desarrollo (redis-dev) que ya usa la cache del
# issue #11 (REDIS_URL) — no introducimos una segunda instancia de Redis ni un broker
# aparte. Se expone como CELERY_BROKER_URL para poder apuntar a otro broker en el futuro
# (ej. el docker-compose final del issue #19) sin tocar la cache; por defecto cae al mismo
# redis://localhost:6379/0.
DEFAULT_BROKER_URL = "redis://localhost:6379/0"
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", os.getenv("REDIS_URL", DEFAULT_BROKER_URL))

# Cómo correr el worker local (proceso aparte del API):
#   uv run celery -A app.infrastructure.tasks.celery_app:celery_app worker --loglevel=info
celery_app = Celery(
    "ia_store",
    broker=CELERY_BROKER_URL,
    include=["app.infrastructure.tasks.catalog_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)


@worker_process_init.connect
def _configure_worker_logging(**kwargs) -> None:
    """Configura structlog en cada proceso hijo del worker de Celery.

    El worker corre en un proceso aparte de FastAPI; `worker_process_init` se dispara
    al iniciar cada proceso hijo (donde se ejecutan las tasks), de modo que los logs de
    `catalog_tasks.py` salgan como JSON igual que en el proceso web.
    """
    configure_logging()
