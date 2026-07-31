from collections import deque
from threading import Lock

from ...domain.entities.conversation_message import ConversationMessage
from ...domain.ports.conversation_memory_port import ConversationMemoryPort

# Cantidad de turnos (par mensaje de usuario + respuesta del agente) que se recuerdan
# por sesión. 5 turnos (=10 mensajes) alcanza para mantener el contexto de una
# conversación de venta típica ("¿tenés zapatillas Nike?" -> "¿cuánto cuestan esas?")
# sin acumular un historial que infle indefinidamente el prompt (y el costo de tokens)
# enviado al LLM en cada request.
MAX_TURNS_PER_SESSION = 5


class InMemoryConversationMemory(ConversationMemoryPort):
    """Implementación en memoria de proceso del `ConversationMemoryPort`.

    Pensada para desarrollo/demo: el historial vive en un dict en memoria, se pierde
    si el proceso se reinicia y no se comparte entre múltiples workers/instancias.
    Para producción con múltiples réplicas habría que reemplazarla por un backend
    compartido (ej. Redis, ver issue #11), pero la interfaz (`ConversationMemoryPort`)
    no cambiaría.
    """

    def __init__(self, max_turns: int = MAX_TURNS_PER_SESSION):
        self._max_turns = max_turns
        self._sessions: dict[str, deque[ConversationMessage]] = {}
        self._lock = Lock()

    def get_history(self, session_id: str) -> list[ConversationMessage]:
        with self._lock:
            return list(self._sessions.get(session_id, ()))

    def add_interaction(self, session_id: str, user_message: str, ai_response: str) -> None:
        with self._lock:
            history = self._sessions.setdefault(
                session_id, deque(maxlen=self._max_turns * 2)
            )
            history.append(ConversationMessage(role="user", content=user_message))
            history.append(ConversationMessage(role="assistant", content=ai_response))


# Instancia única a nivel de módulo: FastAPI resuelve un `ProductService`/`ProductRepository`
# nuevo por request (atados a la sesión de DB de esa request), pero la memoria de
# conversación debe persistir entre requests mientras el proceso viva. Se expone vía
# `get_conversation_memory` para inyectarla con `Depends`, igual que `get_db`.
conversation_memory = InMemoryConversationMemory()


def get_conversation_memory() -> ConversationMemoryPort:
    return conversation_memory
