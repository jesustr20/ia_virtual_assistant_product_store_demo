from fastapi import APIRouter, Depends
from ..schemas.router_schemas import RouteMessageRequest, RouteMessageResponse
from ..dependencies import enforce_prompt_injection_safety, enforce_rate_limit
from ...domain.ports.rate_limiter_port import RateLimiterPort
from ...infrastructure.rate_limiting.redis_rate_limiter import get_rate_limiter
from ...infrastructure.llm.gemini_router_adapter import GeminiRouterAdapter
from ...infrastructure.cache.redis_cache_adapter import get_cache
from ...domain.ports.cache_port import CachePort
from ...application.route_message import RouteMessageService

router = APIRouter()

def get_route_service(cache: CachePort = Depends(get_cache)) -> RouteMessageService:
    adapter = GeminiRouterAdapter()
    return RouteMessageService(adapter, cache)

@router.post("/route", response_model=RouteMessageResponse)
def route_message(
    request: RouteMessageRequest,
    rate_limiter: RateLimiterPort = Depends(get_rate_limiter),
    service: RouteMessageService = Depends(get_route_service),
):
    enforce_rate_limit(request.session_id, rate_limiter)
    enforce_prompt_injection_safety(request.message, request.session_id)
    category = service.route(request.message)
    return RouteMessageResponse(category=category)
