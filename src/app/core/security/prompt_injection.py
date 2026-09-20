"""Detección de intentos de prompt injection en mensajes de usuario (issue #22).

MITIGACIÓN, NO ELIMINACIÓN
--------------------------
No existe una defensa 100% efectiva contra prompt injection hoy. Este módulo detecta un
subconjunto RAZONABLE de los patrones más comunes (categoría LLM01 del OWASP Top 10 for
LLM Applications): instrucciones que intentan sobreescribir el comportamiento del sistema
o extraer el system prompt. Un atacante motivado puede reformular el mensaje para evadir
estas reglas (sinónimos, leetspeak, instrucciones indirectas, otro idioma, etc.). Por eso
esto se documenta como *mitigación* —frena los ataques obvios y deja registro para
revisión—, no como una barrera completa.

La lista de patrones es deliberadamente CONSERVADORA (frases muy explícitas) para
minimizar falsos positivos: en un bot de ventas, bloquear un mensaje legítimo de un
cliente ("¿tenés zapatillas talla 42?") tiene un costo real de UX.
"""

import hashlib
import re
from dataclasses import dataclass

# Cada regla es `(nombre, regex)`. El `nombre` identifica la regla en los logs para saber
# QUÉ patrón disparó, sin necesidad de loguear el mensaje completo (privacidad).
#
# Los regex se evalúan sobre el mensaje normalizado (minúsculas, espacios colapsados) y
# son case-insensitive; las tildes se cubren con clases tipo `[áa]` para tolerar tanto
# "actúa" como "actua". `[^.!?\n]{0,N}` permite separar el verbo del objeto en una misma
# frase sin cruzar límites de oración (evita combinar palabras de oraciones distintas).
#
# Para extender la lista basta con agregar una tupla. Regla de oro para no introducir
# falsos positivos: usar frases tan explícitas que sean muy improbables en una consulta
# legítima de catálogo/ventas.
INJECTION_PATTERNS: tuple[tuple[str, str], ...] = (
    (
        "ignore_previous_instructions",
        r"\b(ignore|ignor[áa]|forget|olvid[áa]|disregard|desestim[áa]|descarta|obvi[áa])\b"
        r"[^.!?\n]{0,60}\b(previous|todas|las|tus|sus|your|all|the)\b"
        r"[^.!?\n]{0,30}\b(instructions?|instrucciones|directives?|directivas|reglas|rules|prompt)\b",
    ),
    (
        "you_are_now",
        r"\b(you are now|now you are|ahora (sos|eres)|sos ahora|eres ahora)\b",
    ),
    (
        "act_as",
        # "act as"/"actúa como" SOLOS no alcanzan: son verbos descriptivos comunes en
        # una consulta de producto ("el termo actúa como aislante"). Exigimos una marca
        # explícita de asignación de ROL: artículo en inglés ("act as a/an/the [rol]")
        # o el hipotético en español ("actúa como si [fueras/fuera...]"). El resto
        # (hacete pasar por, hacé de cuenta, simulá que, fingé que) ya implican
        # role-play por su propia construcción.
        r"\b(act as (a|an|the)|act[úu][áa] como si|hacete pasar por|hac[ée] de cuenta|"
        r"simul[áa] que|fing[eí] que)\b",
    ),
    (
        "disregard_the_above",
        r"\b(disregard|ignor[áa]|desestim[áa]|descarta|haz caso omiso|hac[ée] caso omiso)\b"
        r"[^.!?\n]{0,30}\b(the above|above|lo anterior|lo de arriba|todo lo anterior)\b",
    ),
    (
        "new_instructions",
        r"\b(new instructions?|nuevas instrucciones|nueva instrucci[óo]n|instrucciones nuevas)\b",
    ),
    (
        "reveal_system_prompt",
        r"\b(reveal|revel[áa]|repeat|repet[íi]|recit[áa]|mostr[áa]|imprim[íi]|print|show|"
        r"decime|dime|cu[áa]l es)\b"
        r"[^.!?\n]{0,40}\b(system prompt|system message|initial prompt|prompt|"
        r"tus instrucciones|your instructions)\b",
    ),
    (
        "forget_everything",
        r"\b(forget|olvid[áa]|borr[áa])\b[^.!?\n]{0,30}\b(todo|everything|lo anterior)\b",
    ),
    (
        "jailbreak_marker",
        r"\b(developer mode|modo desarrollador|jailbreak|do anything now|dan mode)\b",
    ),
    (
        "role_override_from_now_on",
        r"\b(from now on|a partir de ahora|de ahora en m[áa]s)\b"
        r"[^.!?\n]{0,50}\b(sos|eres|you are|actu[áa]s|you act)\b",
    ),
)


@dataclass(frozen=True)
class PromptInjectionResult:
    """Resultado de la detección: si hubo match y qué reglas dispararon."""

    is_suspicious: bool
    matched_patterns: tuple[str, ...] = ()


def detect_prompt_injection(message: str) -> PromptInjectionResult:
    """Detecta patrones comunes de prompt injection en `message`.

    Función PURA (sin I/O ni dependencias externas): normaliza, evalúa las reglas y
    devuelve qué patrones matchearon. No loguea ni levanta excepciones —esas decisiones
    quedan en el caller (ver `enforce_prompt_injection_safety` en `api/dependencies.py`),
    lo que la hace trivial de testear en unit tests.
    """
    normalized = _normalize(message)
    matched = tuple(
        name for name, pattern in _COMPILED_PATTERNS if pattern.search(normalized)
    )
    return PromptInjectionResult(is_suspicious=bool(matched), matched_patterns=matched)


def message_fingerprint(message: str) -> str:
    """Hash sha256 del mensaje normalizado, para correlacionar en logs SIN guardar el
    texto completo del cliente (mismo criterio de privacidad que `build_cache_key`,
    issue #11). Permite detectar intentos repetidos del mismo atacante sin persistir
    contenido sensible.
    """
    return hashlib.sha256(_normalize(message).encode("utf-8")).hexdigest()


def _normalize(message: str) -> str:
    """Minúsculas + colapso de espacios. No se tocan las tildes: los regex ya las cubren."""
    return " ".join(message.lower().split())


_COMPILED_PATTERNS: tuple[tuple[str, re.Pattern], ...] = tuple(
    (name, re.compile(pattern, re.IGNORECASE)) for name, pattern in INJECTION_PATTERNS
)
