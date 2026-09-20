from pydantic import BaseModel, Field

class RouteMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    session_id: str = Field(
        min_length=1,
        max_length=100,
        description="Identificador de la conversación, generado por el cliente y "
        "reenviado en cada mensaje de la misma sesión. /ai/route comparte identidad de "
        "rate limiting con /ai/catalogo a través de este campo.",
    )

class RouteMessageResponse(BaseModel):
    category: str