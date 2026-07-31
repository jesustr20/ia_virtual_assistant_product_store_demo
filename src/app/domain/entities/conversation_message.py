from typing import Literal

from pydantic import BaseModel, Field


class ConversationMessage(BaseModel):
    role: Literal["user", "assistant"] = Field(
        description="Quién emitió el mensaje dentro de la conversación"
    )
    content: str = Field(description="Contenido textual del mensaje")
