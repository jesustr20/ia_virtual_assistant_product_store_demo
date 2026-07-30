from pydantic import BaseModel, Field

class RouteMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)

class RouteMessageResponse(BaseModel):
    category: str