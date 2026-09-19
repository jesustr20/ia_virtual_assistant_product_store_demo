import logging
import os

import redis
from dotenv import load_dotenv

from ...domain.ports.cache_port import CachePort

load_dotenv()

logger = logging.getLogger("app")

DEFAULT_REDIS_URL = "redis://localhost:6379/0"


class RedisCacheAdapter(CachePort):
    """Implementación de CachePort usando Redis.

    Es *fail-open*: si Redis no responde (contenedor caído, red, etc.), `get`
    devuelve None (se trata como cache miss y se llama al LLM directamente) y `set`
    no hace nada. La cache es una optimización de costo/latencia, no la fuente de
    verdad; una caída de Redis nunca debe romper el request. Por eso acá capturamos
    `redis.exceptions.RedisError` y logueamos, en vez de propagar una AppException
    (que está pensada para errores de negocio que sí debe ver el cliente, no para
    degradación de una dependencia opcional).
    """

    def __init__(self, url: str | None = None):
        self._url = url or os.getenv("REDIS_URL", DEFAULT_REDIS_URL)
        self._client = redis.Redis.from_url(
            self._url,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )

    def get(self, key: str) -> str | None:
        try:
            return self._client.get(key)
        except redis.exceptions.RedisError:
            logger.exception("Redis no disponible al leer la clave %s", key)
            return None

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        try:
            self._client.set(key, value, ex=ttl_seconds)
        except redis.exceptions.RedisError:
            logger.exception("Redis no disponible al escribir la clave %s", key)


# Instancia única a nivel de módulo: un solo cliente de Redis por proceso, inyectado
# vía Depends (mismo patrón que get_vector_store y get_conversation_memory).
cache = RedisCacheAdapter()


def get_cache() -> CachePort:
    return cache
