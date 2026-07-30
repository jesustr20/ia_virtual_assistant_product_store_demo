from typing import Literal
from pydantic import BaseModel, Field

class RouteDecision(BaseModel):
    category: Literal["CATALOGO", "VENTAS", "SOPORTE"] = Field(
        description="Categoría del agente que debe responder al mensaje del usuario"
    )