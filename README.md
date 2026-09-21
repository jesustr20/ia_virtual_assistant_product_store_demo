# ia_virtual_assistant_product_store_demo

Asistente de ventas multi-agente para una tienda de productos, construido con FastAPI +
LangChain + LangGraph. Proyecto de **portfolio** para un puesto de Backend Engineer AI —
27 issues de funcionalidad + 6 issues de seguridad dedicada, cada uno con su propio PR,
revisión, y pruebas reales documentadas en el historial de GitHub.

## Qué hace

Un cliente le escribe al bot ("¿tenés zapatillas para correr?"), un **router** clasifica
la intención, y un **agente de Catálogo** responde usando **RAG real** sobre el catálogo
(ChromaDB + embeddings de Gemini) — nunca inventa stock ni precios, siempre los consulta
en vivo contra la base de datos. El agente recuerda el contexto de la conversación
("¿cuánto cuestan esas?" resuelve correctamente contra lo hablado antes), y todo el flujo
está protegido contra prompt injection, rate-limiteado, y auditado.

```
Cliente
   │
   ▼
Router (Gemini, clasifica la intención)
   │
   ▼
Agente de Catálogo (Gemini + LangGraph + tool calling)
   │
   ├── buscar_producto      → búsqueda semántica (ChromaDB)
   ├── consultar_stock      → PostgreSQL en vivo
   └── calcular_precio      → PostgreSQL en vivo
```

**Estado honesto:** el agente de **Catálogo** está completo y funcional de punta a punta.
Los agentes de **Ventas** y **Soporte** son, por ahora, solo categorías de clasificación
del router — no tienen tools ni lógica de negocio propia (no existe gestión de órdenes
en este proyecto). Esta decisión y su razonamiento están documentados en el
[issue #23](../../issues) y en `OWASP_LLM_CHECKLIST.md` (categoría LLM03).

## Stack

| Capa | Tecnología |
|---|---|
| API | FastAPI (Python 3.12, async) |
| Orquestación de agentes | LangChain + LangGraph |
| LLM | Google Gemini (`gemini-3.5-flash-lite`), vía `langchain-google-genai` |
| RAG | ChromaDB (modo cliente/servidor) + embeddings de Gemini |
| Base de datos | PostgreSQL + SQLAlchemy + Alembic |
| Cache / rate limiting / broker | Redis |
| Tareas en background | Celery |
| Auth | JWT (roles admin/user) |
| Logging | structlog (JSON estructurado) |
| Error tracking | Sentry |
| Gestor de paquetes | uv |
| Contenedores | Docker (multi-stage, no-root) + Docker Compose |
| CI | GitHub Actions (lint, tests, escaneo de dependencias, build de imagen) |

## Arquitectura del código

Hexagonal liviana — dominio y aplicación no dependen de infraestructura:

```
src/app/
├── domain/           # entidades y puertos (contratos)
├── application/       # casos de uso (servicios)
├── infrastructure/    # implementaciones concretas (DB, LLMs, cache, seguridad)
└── api/               # routers FastAPI y schemas Pydantic
```

Convenciones completas de desarrollo en [`AGENTS.md`](AGENTS.md) (pensado también para
que un agente de IA pueda contribuir al proyecto siguiendo las mismas reglas).

## Cómo correrlo

### Opción recomendada: Docker Compose

Funciona igual en Windows, Mac o Linux — es el único camino garantizado
multiplataforma, ya que todo corre dentro de contenedores Linux.

```bash
git clone https://github.com/jesustr20/ia_virtual_assistant_product_store_demo.git
cd ia_virtual_assistant_product_store_demo
cp .env.example .env   # completar con tus claves reales (ver tabla abajo)
docker compose up --build
```

Esto levanta 5 servicios: `api` (FastAPI, corre las migraciones de Alembic solo),
`worker` (Celery, reindexado en background), `postgres`, `redis`, `chroma`.

Swagger interactivo disponible en `http://localhost:8000/docs`.

### Alternativa: correr sin Docker (avanzado)

Requiere Postgres, Redis y ChromaDB corriendo localmente por tu cuenta. El
comportamiento puede variar según tu sistema operativo (algunas dependencias no
tienen wheels precompiladas para todas las combinaciones de SO/arquitectura).

```bash
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --app-dir src --reload
# en otra terminal:
uv run celery -A app.infrastructure.tasks.celery_app:celery_app worker --loglevel=info
```

### Variables de entorno

Ver [`.env.example`](.env.example) para la lista completa. Las más importantes:

| Variable | Para qué |
|---|---|
| `GEMINI_API_KEY` | LLM y embeddings ([aistudio.google.com/apikey](https://aistudio.google.com/apikey)) |
| `SECRET_KEY` | Firma de JWT — generar con `python3 -c "import secrets; print(secrets.token_hex(32))"` |
| `DATABASE_URL` | Conexión a PostgreSQL |
| `REDIS_URL` / `CELERY_BROKER_URL` | Cache, rate limiting, y broker de Celery |
| `CHROMA_HOST` / `CHROMA_PORT` | Servidor de ChromaDB |
| `SENTRY_DSN` | Opcional — error tracking (vacío = deshabilitado) |

Gestión de secretos, rotación de claves, y controles de GitHub habilitados están
documentados en [`SECURITY.md`](SECURITY.md).

## Ejemplos de uso (curl)

### Flujo 1 — Autenticación (panel de administración)

El JWT protege únicamente la administración del catálogo. El chat con los agentes es
público, sin login (ver Flujo 3) — así funcionaría con un cliente real hablando por
WhatsApp, identificado por su número, no por usuario/contraseña.

```bash
# El PRIMER usuario que se registra en el sistema queda como admin automáticamente.
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "unaPasswordSegura123", "password_repeat": "unaPasswordSegura123"}'

# Login — guardamos el token en una variable para reusarlo
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "unaPasswordSegura123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

### Flujo 2 — Administración del catálogo

Crear, editar y borrar productos requiere el token de un admin. Leer el catálogo es
público (cualquiera puede listar/ver productos sin loguearse).

```bash
# Crear un producto (requiere token de admin)
curl -X POST http://localhost:8000/product/products \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name": "Zapatillas Running Pro", "description": "Livianas, para correr largas distancias", "price": 89.99, "stock": 15}'

# Listar productos (sin autenticación)
curl http://localhost:8000/product/products

# Editar un producto (requiere token de admin) — el catálogo vectorial se reindexa solo
curl -X PUT http://localhost:8000/product/products/1 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name": "Zapatillas Running Pro", "description": "Livianas, para correr largas distancias", "price": 79.99, "stock": 20}'

# Borrar un producto (requiere token de admin)
curl -X DELETE http://localhost:8000/product/products/1 \
  -H "Authorization: Bearer $TOKEN"
```

### Flujo 3 — Chatear con el agente de Catálogo (público, sin login)

`session_id` identifica una conversación — reenvialo en cada mensaje del mismo cliente
para que el agente recuerde el contexto entre turnos.

```bash
SESSION_ID="cliente-demo-001"

# Primer mensaje — el agente busca semánticamente, no por texto exacto
curl -X POST http://localhost:8000/ai/catalogo \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"busco calzado deportivo para correr\", \"session_id\": \"$SESSION_ID\"}"

# Segundo mensaje, misma sesión — "esas" se resuelve contra el turno anterior
curl -X POST http://localhost:8000/ai/catalogo \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"¿cuánto cuestan esas?\", \"session_id\": \"$SESSION_ID\"}"

# Variante streaming (Server-Sent Events, respuesta token por token)
curl -N -X POST http://localhost:8000/ai/catalogo/stream \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"¿tenés algo para acampar de noche?\", \"session_id\": \"$SESSION_ID\"}"
```

### Flujo 4 — Solo clasificar intención (sin invocar al agente completo)

```bash
curl -X POST http://localhost:8000/ai/route \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"quiero comprar 2 unidades\", \"session_id\": \"$SESSION_ID\"}"
# → {"category": "VENTAS"}
```

## Tests y CI

```bash
uv run pytest              # tests unitarios (lógica de negocio, sin servicios reales)
uv run ruff check .        # lint
uv run pip-audit           # dependencias vulnerables
```

Cada Pull Request corre automáticamente: lint → tests → escaneo de dependencias →
smoke test de arranque → build de la imagen Docker. Ver
[`.github/workflows/ci.yml`](.github/workflows/ci.yml).

## Seguridad

Este proyecto tiene una fase dedicada de seguridad (6 issues), con documentación honesta
de qué está mitigado y qué es una limitación conocida — no un checklist inflado:

- [`SECURITY.md`](SECURITY.md) — gestión de secretos, rotación de claves, análisis de
  CVEs de dependencias (pip-audit) y de la imagen Docker (Trivy).
- [`OWASP_LLM_CHECKLIST.md`](OWASP_LLM_CHECKLIST.md) — las 10 categorías del OWASP Top
  10 for LLM Applications (2026), aplicadas contra el código real del proyecto.

## Historial de desarrollo

Todo el proyecto se construyó issue por issue, con Pull Requests individuales, CI en
verde antes de cada merge, y revisión de código en cada PR (incluyendo bugs reales
encontrados y corregidos durante la revisión — cache compartida entre sesiones, rate
limiting rompiendo el acceso público, una race condition en un cliente HTTP lazy, entre
otros). El historial completo de [issues](../../issues?q=is%3Aissue+is%3Aclosed) y
[pull requests](../../pulls?q=is%3Apr+is%3Aclosed) queda como registro de ese proceso.

## Autoría

Desarrollado por **Jesús** ([@jesustr20](https://github.com/jesustr20)), con asistencia
de IA a lo largo de todo el proceso: diseño arquitectónico y revisión de código con
Claude (Anthropic), e implementación de features con agentes de código (Claude y
DeepSeek vía OpenCode). Cada pieza de código generado por un agente fue revisada
explícitamente antes de mergear — el proceso de revisión (incluyendo desacuerdos,
correcciones, y bugs reales encontrados) es parte intencional de lo que este proyecto
demuestra.
