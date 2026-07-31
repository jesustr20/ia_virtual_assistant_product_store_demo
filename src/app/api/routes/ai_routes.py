from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.infrastructure.llm.gemini_adapter import GeminiService
from app.infrastructure.llm.catalog_agent import run_catalog_agent
from app.infrastructure.db.session import get_db
from app.infrastructure.db.product_repository import ProductRepository
from app.infrastructure.memory.in_memory_conversation_memory import get_conversation_memory
from app.application.product_service import ProductService
from app.domain.ports.conversation_memory_port import ConversationMemoryPort
from app.api.schemas.ai_schemas import AskAIRequest, CatalogAgentRequest, CatalogAgentResponse
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

@router.post("/ask_ai")
def ask_ai(request: AskAIRequest, db: Session = Depends(get_db)):
    gemini_service = GeminiService(api_key=os.getenv("GEMINI_API_KEY"), product_repo=ProductRepository(db))
    if "producto" in request.question.lower():
        return {"respuesta": gemini_service.respond_with_products(request.question)}
    else:
        return {"respuesta": gemini_service.get_humanlike_response(request.question)}

@router.post("/catalogo", response_model=CatalogAgentResponse)
def catalogo(
    request: CatalogAgentRequest,
    db: Session = Depends(get_db),
    memory: ConversationMemoryPort = Depends(get_conversation_memory),
):
    product_service = ProductService(ProductRepository(db))
    history = memory.get_history(request.session_id)
    response = run_catalog_agent(product_service, request.message, history=history)
    memory.add_interaction(request.session_id, request.message, response)
    return CatalogAgentResponse(response=response)