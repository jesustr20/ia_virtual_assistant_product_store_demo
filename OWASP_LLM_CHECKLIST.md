# OWASP Top 10 for LLM Applications — checklist aplicado al proyecto

Edición de referencia: **OWASP Top 10 for LLM Applications 2026** (agosto 2026). Cada
categoría se mapea contra el estado real del código (`src/app/`), no de memoria. Los
estados posibles son **Mitigated / Partial / Not Applicable / Known Gap**, y por cada una
se indica qué hace el proyecto, referenciando el issue/mecanismo concreto, y el **riesgo
residual honesto** (sin sobreestimar la protección).

## Resumen

| # | Categoría | Estado | Mecanismo principal |
|---|---|---|---|
| LLM01 | Prompt Injection | Partial | Detección por regex (#22) en `/catalogo`, `/catalogo/stream`, `/route` |
| LLM02 | Sensitive Information Disclosure | Mitigated | No PII en prompts/logs, Sentry sin PII (#17), fingerprints en vez de texto |
| LLM03 | Excessive Agency | Mitigated | Registro de capacidades (#23): el agente solo recibe sus tools |
| LLM04 | Supply Chain | Partial | pip-audit (#25) + Dependabot + Trivy (#26); modelo es API hosteada |
| LLM05 | Data and Model Poisoning | Not Applicable | No hay training/fine-tuning; RAG alimentado solo por admin (#2) |
| LLM06 | Unbounded Consumption | Partial | Rate limiting (#13) + cost tracing (#16); sin tope duro de gasto |
| LLM07 | Misinformation | Partial | RAG grounding (#9) + tools que leen datos en vivo (#7); no elimina alucinación |
| LLM08 | Hidden Context Exposure | Mitigated | System prompts sin secretos/PII + bloqueo de extracción (#22) |
| LLM09 | Vector and Embedding Weaknesses | Not Applicable | Una sola colección compartida (catálogo público); sin datos por usuario |
| LLM10 | Improper Output Handling | Not Applicable | Salida como texto plano a JSON/SSE; nunca alimenta SQL/shell/HTML |

---

## LLM01 — Prompt Injection — **Partial**

**Qué hace el proyecto.** `core/security/prompt_injection.py` (#22) detecta patrones
explícitos de inyección ("ignorá tus instrucciones", "actuá como…", "revelá tu system
prompt", marcadores de jailbreak) con regex conservadores, y
`api/dependencies.py:enforce_prompt_injection_safety` los rechaza con 400 **antes** de
gastar una llamada al LLM. Se aplica en `/catalogo`, `/catalogo/stream` y `/route`.

**Riesgo residual honesto.** El propio módulo lo declara: es **mitigación, no
eliminación**. Un atacante motivado evade los patrones (sinónimos, leetspeak, otro
idioma, instrucciones indirectas). Además hay **un endpoint sin protección**:
`/ai/ask_ai` (legacy, `ai_routes.py`) llama a Gemini directo (`GeminiService`) **sin**
`enforce_prompt_injection_safety` ni rate limiting. La frontera de negocio real la aporta
LLM03 (el agente no tiene tools peligrosas), no esta detección.

---

## LLM02 — Sensitive Information Disclosure — **Mitigated**

**Qué hace el proyecto.** Los logs nunca escriben el mensaje completo del cliente:
`message_fingerprint` (#22) y `build_cache_key` (#11) guardan hashes sha256; la detección
de inyección loguea solo `session_id`, `matched_patterns` y fingerprint.
`core/logging_config.py` (#15) emite structlog→JSON sin datos de negocio.
`core/sentry_config.py` (#17) fija `send_default_pii=False` y descarta `AppException`.
Los system prompts no contienen secretos ni PII. El proyecto **no recolecta datos
personales sensibles** (sin DNI/edad; ver AGENTS.md).

**Riesgo residual honesto.** La memoria de conversación (`in_memory_conversation_memory`,
#8) está indexada por un `session_id` **provisto por el cliente** y sin autenticación: no
hay endpoint que liste sesiones, pero quien adivine/obtenga un `session_id` ajeno leería
ese historial. Hoy contiene solo charla de catálogo (sin PII), por lo que el impacto es
bajo; si más adelante la conversación incluyera datos sensibles, este aislamiento por
`session_id` dejaría de alcanzar.

---

## LLM03 — Excessive Agency — **Mitigated**

**Qué hace el proyecto.** `core/security/agent_capabilities.py` (#23) es la fuente de
verdad de qué tools recibe cada agente; `catalog_agent.build_catalog_agent` deriva el set
de tools vía `select_allowed_tools("catalogo", ...)`, no lo hardcodea. El agente de
catálogo solo tiene `buscar_producto`, `consultar_stock`, `calcular_precio` — ninguna
crea/cancela órdenes, procesa pagos ni hace reembolsos (esa funcionalidad **no existe**,
y el system prompt lo declara).

**Riesgo residual honesto.** Es el control más sólido del proyecto: el agente **ni
siquiera tiene** la herramienta para excederse. La limitación documentada (#23) es que
**VENTAS y SOPORTE no existen como agentes** (son solo categorías del router #6), así que
hoy no hay más superficie de agencia. Cuando se implementen, sus tools deberán registrarse
en `AGENT_TOOLS` o no llegarán al agente — esa es exactamente la frontera que garantiza
este módulo.

---

## LLM04 — Supply Chain — **Partial**

**Qué hace el proyecto.** La cadena de **dependencias de software** está escaneada:
`pip-audit` en CI (#25) + Dependabot alerts + escaneo de imagen con Trivy (#26). El
**modelo** no se descarga como artefacto: Gemini se consume como **API hosteada** (vía
`langchain-google-genai` en el router/agente), sin archivo de pesos local, sin
`trust_remote_code`, sin repo de modelos de HuggingFace — así que el riesgo clásico de
"modelo sustituido/manipulado" **no aplica**.

**Riesgo residual honesto.** Dos detalles. (1) El modelo se invoca por **alias**
(`gemini-3.5-flash-lite`, ver `tracing.py`): Google puede cambiar a qué versión apunta ese
nombre sin que el proyecto lo fije, lo cual es una forma menor de riesgo de cadena. (2)
Queda un **camino legacy** (`gemini_adapter.py`, usado por `/ai/ask_ai`) que importa el
paquete deprecado `google-generativeai` (AGENTS.md indica no usarlo) — es código a retirar,
no un riesgo de seguridad agudo.

---

## LLM05 — Data and Model Poisoning — **Not Applicable**

**Qué hace el proyecto.** El proyecto **no entrena ni hace fine-tuning** de ningún modelo:
no hay datos de entrenamiento que envenenar. El único "dato que alimenta al modelo" es el
catálogo indexado en ChromaDB vía RAG (#9/#10), y ese ingreso está **protegido por
autenticación** (crear/editar/borrar producto requieren `get_current_user`, issue #2).

**Riesgo residual honesto.** Un ángulo menor a nombrar: una **descripción de producto
maliciosa** (creada por un admin legítimo o por un admin comprometido) se indexa y podría
influir en las respuestas del agente. La mitigación práctica es que las tools de catálogo
**releen el dato en vivo de la DB** (`product_tools.buscar_producto` llama
`get_product_by_id`) en lugar de confiar en el texto cacheado del vector, así que el
impacto de un texto envenenado en el índice es bajo. No hay entrenamiento que proteger.

---

## LLM06 — Unbounded Consumption — **Partial**

**Qué hace el proyecto.** `RedisRateLimiter` (#13) limita a 20 mensajes/minuto por sesión
en `/catalogo`, `/catalogo/stream` y `/route`. `tracing.py` (#16) loguea latencia, tokens
y `estimated_cost_usd` por llamada (observabilidad de costo).

**Riesgo residual honesto (gap).** **No existe un tope duro de gasto** ni alerta de
presupuesto: el rate limit es la única barrera y es (a) *fail-open* (si Redis cae, se
deja pasar), (b) **por `session_id` provisto por el cliente**, trivial de rotar para
esquivarlo (no hay límite por IP/usuario porque los endpoints de chat son públicos), y
(c) no cubre `/ai/ask_ai`. El cost tracing mide, no limita. → **Gap conocido** (issue
futuro: tope de gasto/alerting por cuenta de Gemini); para un portfolio es aceptable,
pero no es "mitigado".

---

## LLM07 — Misinformation — **Partial**

**Qué hace el proyecto.** El agente de catálogo está **groundeado**: usa RAG (#9) para
recuperar productos reales y sus tools (#7) consultan **precio/stock en vivo** desde la DB
(`consultar_stock`, `calcular_precio`, y `buscar_producto` re-lee `get_product_by_id`),
en vez de confiar en el texto cacheado del vector. El system prompt instruye "usá siempre
tus herramientas con datos reales; nunca inventes".

**Riesgo residual honesto.** Esto **reduce** la probabilidad de alucinación pero **no la
elimina**: el modelo puede entre llamadas a tools resumir mal, inventar un atributo, o
afirmar algo fuera del catálogo. No hay verificación del output final contra la DB ni
guardrails que bloqueen afirmaciones no sustentadas. Para un bot de catálogo el daño es
bajo (información de producto), pero no es "mitigado".

---

## LLM08 — Hidden Context Exposure — **Mitigated**

**Qué hace el proyecto.** Los system prompts (`catalog_agent.SYSTEM_PROMPT`,
`gemini_router_adapter.SYSTEM_PROMPT`) **no contienen secretos, credenciales ni PII**: solo
describen el rol, las capacidades y las limitaciones del bot. El patrón
`reveal_system_prompt` de #22 bloquea los intentos obvios de extracción ("revelá tu system
prompt", "cuál es tu prompt") — cross-referencia a LLM01, no se re-analiza.

**Riesgo residual honesto.** La extracción de prompt nunca es 100% prevenible (ver LLM01),
pero el **impacto** es bajo: lo único "oculto" es la descripción del rol, que ya es
reconstruible observando el comportamiento. No hay nada dañino que filtrar.

---

## LLM09 — Vector and Embedding Weaknesses — **Not Applicable**

**Qué hace el proyecto.** El vector store es **una única colección compartida**
(`"products"`, `chromadb_adapter.py`) con el catálogo **público** de la tienda — no hay
datos por usuario ni multi-tenant que aislar, así que **no existe riesgo de fuga
cross-tenant**. Los embeddings se generan server-side (Gemini) a partir del texto del
producto; no se aceptan embeddings provistos por el cliente.

**Riesgo residual honesto.** La debilidad real del vector store **no es de multi-tenant**
sino de infraestructura: ChromaDB corre **sin autenticación** y (en compose) no expone su
puerto — ya documentado y analizado en SECURITY.md (issues #25/#26). Mientras el catálogo
siga siendo público y de una sola colección, esta categoría no aplica; si algún día se
guardaran embeddings de datos privados por cliente, reaparecería.

---

## LLM10 — Improper Output Handling — **Not Applicable**

**Qué hace el proyecto.** La salida del LLM se devuelve **como texto plano** al cliente:
`CatalogAgentResponse(response=...)` (JSON) o eventos SSE `data: {"text": ...}`
(`ai_routes.py`). La clasificación del router se acota a un `Literal["CATALOGO",
"VENTAS", "SOPORTE"]` (Pydantic). Verificado: la salida del LLM **no** se usa para
construir SQL, ni se ejecuta en shell, ni se interpreta como HTML/JS, ni dispara writes a
la DB (el agente no tiene tools de escritura).

**Riesgo residual honesto.** No hay un camino de "output handling" explotable dentro del
servidor. El residuo es que el **cliente** (frontend/WhatsApp) podría renderizar la
respuesta sin sanitizar — fuera del scope del backend. Si algún día el agente tuviera
tools de escritura o se consumiera su output para operaciones sensibles, esta categoría
pasaría a ser relevante.
