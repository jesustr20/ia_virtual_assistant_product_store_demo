from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .api.routes.router_routes import router as router_router
from .api.routes.ai_routes import router as ai_router
from .api.routes.product_routes import router as product_router
from .api.routes.auth_routes import router as auth_router
from .core.exceptions import AppException
from .core.error_handlers import (
    app_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
)

app = FastAPI()

app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

app.include_router(ai_router, prefix="/ai", tags=["IA"])
app.include_router(product_router, prefix="/product", tags=["Productos"])
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(router_router, prefix="/ai", tags=["Router"])