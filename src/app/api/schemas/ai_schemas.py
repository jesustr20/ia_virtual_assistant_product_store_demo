from pydantic import BaseModel, Field

class AskAIRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)

class CatalogAgentRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)

class CatalogAgentResponse(BaseModel):
    response: str