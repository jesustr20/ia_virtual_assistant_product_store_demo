from abc import ABC, abstractmethod


class RateLimiterPort(ABC):
    """Puerto para limitar la frecuencia de requests por clave.

    Es una preocupación distinta de `CachePort` (issue #11): acá no se guarda ni
    recupera un valor, sino que se incrementa un contador atómico con TTL y se decide
    si la clave sigue dentro del límite. Comparten backend (Redis) pero no semántica:
    "cachear una respuesta" ≠ "contar requests en una ventana". Por eso merece su
    propio puerto/adaptador en vez de ensanchar `CachePort`.
    """

    @abstractmethod
    def is_allowed(self, key: str, limit: int, window_seconds: int) -> bool:
        """Registra un request para `key` y devuelve True si sigue dentro del límite.

        El registro (incremento del contador) es un efecto secundario: aun cuando el
        resultado sea False (rechazo), el intento ya quedó contabilizado.
        """
