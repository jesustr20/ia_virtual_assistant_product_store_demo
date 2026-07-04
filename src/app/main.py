from fastapi import FastAPI
from .db import init_db, SessionLocal
from .endpoints import ai_endpoints
from .endpoints.product_endpoints import router as product_router

app = FastAPI()

@app.on_event("startup")
def startup():
    init_db()

app.include_router(ai_endpoints.router, prefix="/ai", tags=["IA"])
app.include_router(product_router, prefix="/product", tags=["Productos"])