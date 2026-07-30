from fastapi import APIRouter, Depends
from ..schemas.router_schemas import RouteMessageRequest, RouteMessageResponse
from ...infrastructure.llm.gemini_router_adapter import GeminiRouterAdapter
from ...application.route_message import RouteMessageService

router = APIRouter()

def get_route_service() -> RouteMessageService:
    adapter = GeminiRouterAdapter()
    return RouteMessageService(adapter)

@router.post("/route", response_model=RouteMessageResponse)
def route_message(request: RouteMessageRequest, service: RouteMessageService = Depends(get_route_service)):
    category = service.route(request.message)
    return RouteMessageResponse(category=category)