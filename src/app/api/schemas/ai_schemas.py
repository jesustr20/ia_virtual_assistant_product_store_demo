from pydantic import BaseModel, Field

class AskAIRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)

class CatalogAgentRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    session_id: str = Field(
        min_length=1,
        max_length=100,
        description="Identificador de la conversación, generado por el cliente y "
        "reenviado en cada mensaje de la misma sesión.",
    )

class CatalogAgentResponse(BaseModel):
    response: str