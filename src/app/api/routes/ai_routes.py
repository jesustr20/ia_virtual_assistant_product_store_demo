from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.infrastructure.llm.gemini_adapter import GeminiService
from app.infrastructure.llm.catalog_agent import run_catalog_agent
from app.infrastructure.db.session import get_db
from app.infrastructure.db.product_repository import ProductRepository
from app.application.product_service import ProductService
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
def catalogo(request: CatalogAgentRequest, db: Session = Depends(get_db)):
    product_service = ProductService(ProductRepository(db))
    response = run_catalog_agent(product_service, request.message)
    return CatalogAgentResponse(response=response)