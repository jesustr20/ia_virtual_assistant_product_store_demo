import logging

import redis

from ...domain.ports.rate_limiter_port import RateLimiterPort
from ..redis_client import redis_client

logger = logging.getLogger("app")

# Ventana fija con INCR + EXPIRE, en un solo script Lua para que sea atómico.
#
# Ventana fija (vs. sliding window): más simple y suficiente para este scope. Tiene el
# caso de borde conocido del "burst en el límite" (20 requests a las 0:59 + 20 a las
# 1:00 = 40 en ~2s), pero para un límite de costo por minuto de un demo/portfolio esa
# imprecisión es aceptable y no justifica la complejidad de una sliding window.
#
# El script hace INCR y, si es el primer request de la ventana (contador == 1), fija el
# TTL. Hacerlo en Lua evita la carrera de dos comandos separados: si el proceso muriera
# entre un INCR y un EXPIRE condicional, la clave quedaría sin TTL y bloquearía al
# usuario para siempre.
_FIXED_WINDOW_INCR_SCRIPT = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return current
"""


class RedisRateLimiter(RateLimiterPort):
    """Implementación de `RateLimiterPort` con ventana fija sobre Redis.

    Es *fail-open* (mismo criterio que la cache, issue #11): si Redis no responde,
    `is_allowed` devuelve True y se loguea. El rate limiting protege contra abuso de
    costo, pero una caída de Redis no debe dejar el asistente inutilizable.
    """

    def __init__(self, client: redis.Redis | None = None):
        self._client = client or redis_client
        self._script = self._client.register_script(_FIXED_WINDOW_INCR_SCRIPT)

    def is_allowed(self, key: str, limit: int, window_seconds: int) -> bool:
        try:
            current = self._script(keys=[key], args=[window_seconds])
            return current <= limit
        except redis.exceptions.RedisError:
            logger.exception(
                "Redis no disponible al aplicar rate limiting a la clave %s", key
            )
            return True


# Instancia única a nivel de módulo, inyectada vía Depends (mismo patrón que
# `get_cache` / `get_conversation_memory`).
rate_limiter = RedisRateLimiter()


def get_rate_limiter() -> RateLimiterPort:
    return rate_limiter
