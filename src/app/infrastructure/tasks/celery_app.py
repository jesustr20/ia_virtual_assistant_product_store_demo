import os

from celery import Celery
from dotenv import load_dotenv

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
