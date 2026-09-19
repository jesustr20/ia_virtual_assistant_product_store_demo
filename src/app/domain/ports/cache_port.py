import hashlib
from abc import ABC, abstractmethod


class CachePort(ABC):
    """Puerto para una cache clave/valor con expiración (TTL).

    Agnóstico del backend concreto (Redis, Memcached, etc.) — las implementaciones
    viven en `infrastructure/cache/`.
    """

    @abstractmethod
    def get(self, key: str) -> str | None:
        """Devuelve el valor cacheado para `key`, o None si no existe o expiró."""

    @abstractmethod
    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        """Guarda `value` bajo `key` con una expiración de `ttl_seconds`."""


def build_cache_key(agent: str, message: str) -> str:
    """Deriva una clave de cache estable y legible a partir de (agente, mensaje).

    - Normaliza el mensaje (minúsculas y colapsa espacios) para que variaciones
      triviales ("Hola" vs "hola  ") produzcan el mismo cache hit.
    - Hashea con sha256 para no guardar el texto completo del mensaje en la clave
      de Redis. El prefijo `agent` evita colisiones entre el router y el agente de
      catálogo aunque el mensaje sea idéntico.
    """
    normalized = " ".join(message.lower().split())
    digest = hashlib.sha256(f"{agent}:{normalized}".encode("utf-8")).hexdigest()
    return f"{agent}:{digest}"
