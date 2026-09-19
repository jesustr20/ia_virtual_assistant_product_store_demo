from ..domain.ports.router_port import RouterPort
from ..domain.ports.cache_port import CachePort, build_cache_key

# TTL de la cache del router. La clasificación de intención (CATALOGO/VENTAS/SOPORTE)
# depende solo del texto del mensaje y cambia muy raramente; 5 minutos es conservador
# y alcanza para absorber preguntas repetidas sin riesgo real de servir una categoría
# obsoleta.
CACHE_AGENT = "route"
CACHE_TTL_SECONDS = 300


class RouteMessageService:
    def __init__(self, router: RouterPort, cache: CachePort):
        self.router = router
        self.cache = cache

    def route(self, message: str) -> str:
        cache_key = build_cache_key(CACHE_AGENT, message)
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        category = self.router.classify(message).category
        self.cache.set(cache_key, category, CACHE_TTL_SECONDS)
        return category
