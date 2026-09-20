"""Registro central de capacidades por agente (issue #23).

Este módulo es la fuente de verdad de QUÉ herramientas puede usar cada agente. No
depende de LangChain ni de infraestructura concreta: solo mapea nombre de agente ->
nombres de tools permitidas.

Por qué existe
--------------
El system prompt puede "pedirle" al LLM que no haga algo, pero eso no es una defensa
real: un usuario puede convencerlo de ignorarlo (prompt injection). La defensa de
verdad es que el agente NI SIQUIERA TENGA la herramienta fuera de su rol. Acá se
concentra esa frontera: una tool que no esté registrada para un agente no llega a ese
agente.

Scope actual (documentado con honestidad)
-----------------------------------------
Hoy existe UN SOLO agente real con lógica de negocio detrás: "catalogo", con sus 3
tools (buscar_producto, consultar_stock, calcular_precio). VENTAS y SOPORTE son
únicamente categorías de clasificación del router (issue #6); NO hay agentes de
Ventas/Soporte implementados ni lógica de negocio real que los respalde (no hay tabla
de órdenes, ni creación de órdenes, ni reembolsos). Registrarlos acá es trabajo FUTURO:
recién cuando exista lógica real detrás de esas capacidades tendrá sentido agregarlas.
Registrar tools que no existen sería código muerto que induce a error. No se inventan
tools ficticias.
"""


# Mapeo agente -> nombres de tools permitidas. El nombre del agente es el identificador
# canónico en minúsculas; NO confundir con las categorías del router ("CATALOGO",
# "VENTAS", "SOPORTE"), que son una clasificación de intención, no agentes con tools.
AGENT_TOOLS: dict[str, frozenset[str]] = {
    "catalogo": frozenset({"buscar_producto", "consultar_stock", "calcular_precio"}),
}


def allowed_tool_names(agent_name: str) -> frozenset[str]:
    """Nombres de tools permitidas para `agent_name` (vacío si el agente no existe)."""
    return AGENT_TOOLS.get(agent_name, frozenset())


def select_allowed_tools(agent_name: str, available_tools: dict) -> list:
    """Filtra `available_tools` (dict `nombre -> tool`) dejando solo las permitidas.

    Es el punto de enforcement: el agente recibe exactamente las tools registradas para
    su nombre. Si alguien define una tool nueva y la agrega a `available_tools` pero NO
    la registra en `AGENT_TOOLS`, no llega al agente —consecuencia natural de esta
    estructura, no de una convención que haya que recordar cumplir.
    """
    allowed = allowed_tool_names(agent_name)
    return [available_tools[name] for name in sorted(allowed) if name in available_tools]
