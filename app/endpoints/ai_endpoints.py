from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.services.gemini_service import GeminiService
from app.db import get_db
from app.repositories import ProductRepository
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

@router.get("/ask_ai")
def ask_ai(question: str, db: Session = Depends(get_db)):
    gemini_service = GeminiService(api_key=os.getenv("GEMINI_API_KEY"), product_repo=ProductRepository(db))
    if "producto" in question.lower():
        return {"respuesta": gemini_service.respond_with_products(question)}
    else:
        return {"respuesta": gemini_service.get_humanlike_response(question)}