from abc import ABC, abstractmethod

from ..entities.conversation_message import ConversationMessage


class ConversationMemoryPort(ABC):
    """Puerto para guardar y recuperar el historial de mensajes de una sesión.

    Una sesión agrupa los turnos de una misma conversación (identificada por
    `session_id`, generado y reenviado por el cliente en cada mensaje).
    """

    @abstractmethod
    def get_history(self, session_id: str) -> list[ConversationMessage]:
        """Devuelve el historial de mensajes recordado para la sesión, en orden cronológico."""

    @abstractmethod
    def add_interaction(self, session_id: str, user_message: str, ai_response: str) -> None:
        """Agrega un turno (mensaje del usuario + respuesta del agente) al historial de la sesión."""
