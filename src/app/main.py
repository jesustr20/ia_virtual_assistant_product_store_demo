from fastapi import FastAPI
from .infrastructure.db.session import init_db, SessionLocal
from .api.routes.ai_routes import router as ai_router
from .api.routes.product_routes import router as product_router

app = FastAPI()

@app.on_event("startup")
def startup():
    init_db()

app.include_router(ai_router, prefix="/ai", tags=["IA"])
app.include_router(product_router, prefix="/product", tags=["Productos"])