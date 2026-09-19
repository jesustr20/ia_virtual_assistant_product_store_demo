from fastapi import APIRouter, Depends
from ..schemas.router_schemas import RouteMessageRequest, RouteMessageResponse
from ...infrastructure.llm.gemini_router_adapter import GeminiRouterAdapter
from ...infrastructure.cache.redis_cache_adapter import get_cache
from ...domain.ports.cache_port import CachePort
from ...application.route_message import RouteMessageService

router = APIRouter()

def get_route_service(cache: CachePort = Depends(get_cache)) -> RouteMessageService:
    adapter = GeminiRouterAdapter()
    return RouteMessageService(adapter, cache)

@router.post("/route", response_model=RouteMessageResponse)
def route_message(request: RouteMessageRequest, service: RouteMessageService = Depends(get_route_service)):
    category = service.route(request.message)
    return RouteMessageResponse(category=category)
