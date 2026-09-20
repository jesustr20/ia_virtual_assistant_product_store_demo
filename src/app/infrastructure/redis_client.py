import os

import redis
from dotenv import load_dotenv

load_dotenv()

DEFAULT_REDIS_URL = "redis://localhost:6379/0"


def build_redis_client(url: str | None = None) -> redis.Redis:
    """Construye un cliente Redis con timeouts cortos y respuestas decodificadas.

    `decode_responses=True` evita decodificar bytes a mano. Los timeouts de 1s hacen
    que una caída de Redis degrade rápido (fail-open) en vez de colgar el request —
    mismo criterio que la cache (issue #11).
    """
    resolved_url = url or os.getenv("REDIS_URL", DEFAULT_REDIS_URL)
    return redis.Redis.from_url(
        resolved_url,
        decode_responses=True,
        socket_connect_timeout=1,
        socket_timeout=1,
    )


# Cliente Redis compartido a nivel de módulo: un único pool de conexiones por
# proceso, reutilizado por la cache (issue #11) y el rate limiting (issue #13).
# Evita abrir dos pools contra el mismo Redis.
redis_client = build_redis_client()
