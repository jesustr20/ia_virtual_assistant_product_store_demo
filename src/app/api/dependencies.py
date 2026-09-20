import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from ..core.exceptions import PromptInjectionError, RateLimitExceededError
from ..core.security.prompt_injection import detect_prompt_injection, message_fingerprint
from ..domain.ports.rate_limiter_port import RateLimiterPort
from ..infrastructure.security.jwt_handler import decode_access_token

logger = structlog.get_logger(component="prompt_injection")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# Límite de requests a los endpoints que llaman un LLM (issue #13).
#
# ¿Por qué 20 por minuto? Una conversación humana normal con el asistente no supera
# un puñado de mensajes por minuto: leer la respuesta, tipear, releer el catálogo
# suma ~4-8 mensajes/min en un ida y vuelta ágil. 20 da holgura para esa interacción
# real (incluidos seguimientos tipo "¿y esas?", "¿cuánto cuestan?") y a la vez frena a
# un script que martilla el endpoint: a 20 msg/min un bot tardaría 3 minutos en quemar
# 60 llamadas, vs. segundos sin límite. Es configurable acá sin tocar el resto.
AI_RATE_LIMIT = 20
AI_RATE_LIMIT_WINDOW_SECONDS = 60

def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    try:
        payload = decode_access_token(token)
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Token Inválido")
        return username
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se pudo validad el token",
            headers={"WWW-Authenticate":"Bearer"},
        )


def enforce_rate_limit(session_id: str, rate_limiter: RateLimiterPort) -> None:
    """Rechaza con 429 si la sesión ya agotó su cuota de mensajes al asistente.

    Se llama DENTRO del handler (no como dependency a nivel de router) porque el rate
    limit necesita el `session_id` que viaja en el body, y una dependency de FastAPI no
    puede leer el body antes de que el handler lo bindee.

    La clave es por `session_id`, no por usuario ni IP: estos endpoints de chat son
    públicos —el cliente habla con el bot sin login (issue #2 protege solo el panel
    admin/productos); en el sistema real se lo identifica por teléfono vía WhatsApp, acá
    por `session_id`. Se usa UNA sola clave para /ai/route y /ai/catalogo para que
    alternar entre endpoints no esquive el límite — la cuota es por sesión, no por
    endpoint.
    """
    key = f"rate_limit:ai:{session_id}"
    if not rate_limiter.is_allowed(key, AI_RATE_LIMIT, AI_RATE_LIMIT_WINDOW_SECONDS):
        raise RateLimitExceededError()


def enforce_prompt_injection_safety(message: str, session_id: str) -> None:
    """Rechaza el mensaje si detecta patrones comunes de prompt injection (issue #22).

    Se llama DENTRO del handler (igual que `enforce_rate_limit`), ANTES de gastar una
    llamada al LLM: la detección es regex en memoria (barata) y un mensaje rechazado no
    debe llegar al router/agente.

    Decisión de diseño — RECHAZO DURO (no flag blando): si detectamos un patrón, la
    request devuelve 400 y el mensaje NUNCA llega al LLM. Se eligió rechazo en vez de
    "loguear y seguir" porque los patrones son lo suficientemente explícitos ("ignorá
    tus instrucciones", "actuá como...") como para que el riesgo de falso positivo sea
    muy bajo, mientras que dejar pasar un mensaje que sobreescribe el system prompt
    compromete las reglas de negocio del bot (descuentos, etc.). Si en producción
    aparecieran falsos positivos, la mitigación puede degradarse a flag blando sin
    tocar la detección: solo cambia este handler.

    Siempre se loguea el intento detectado (para revisión), con `session_id`, los
    patrones que matchearon y un fingerprint sha256 del mensaje —pero NO el texto
    completo, que puede contener datos personales del cliente.
    """
    result = detect_prompt_injection(message)
    if not result.is_suspicious:
        return

    logger.warning(
        "prompt_injection_detected",
        session_id=session_id,
        matched_patterns=list(result.matched_patterns),
        message_fingerprint=message_fingerprint(message),
    )
    raise PromptInjectionError()
