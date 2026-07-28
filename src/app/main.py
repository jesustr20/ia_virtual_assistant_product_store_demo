from fastapi import FastAPI
from .api.routes.ai_routes import router as ai_router
from .api.routes.product_routes import router as product_router
from .api.routes.auth_routes import router as auth_router

app = FastAPI()

app.include_router(ai_router, prefix="/ai", tags=["IA"])
app.include_router(product_router, prefix="/product", tags=["Productos"])
app.include_router(auth_router, prefix="/auth", tags=["Auth"])