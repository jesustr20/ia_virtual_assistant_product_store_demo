# AGENTS.md — ia_virtual_assistant_product_store_demo

## Qué es este proyecto

Asistente de ventas multi-agente para una tienda de productos, con 3 agentes especializados
(Catálogo, Ventas, Soporte) coordinados por un router. Es un proyecto de **portfolio** dirigido
a un puesto de Backend Engineer AI — la calidad del código y las decisiones de arquitectura
importan tanto como que funcione.

## Antes de tocar código

1. **Consultá CodeGraph primero** para entender estructura, símbolos relacionados, y quién
   llama a qué. Solo leé un archivo completo si CodeGraph no dio suficiente contexto.
2. Revisá el issue de GitHub correspondiente (`gh issue view <número>`) — cada uno tiene
   objetivo, justificación, y criterios de aceptación explícitos. No improvises alcance
   fuera de lo que el issue pide.

## Stack

- Python 3.12, FastAPI, gestor de paquetes **uv** (no pip, no poetry)
- PostgreSQL + SQLAlchemy + Alembic para migraciones (nunca `Base.metadata.create_all` en
  producción — el esquema se gestiona 100% vía Alembic)
- Auth: JWT con `pyjwt` + `pwdlib[argon2]` (no bcrypt directo, no python-jose)
- LLMs: Gemini (vía `langchain-google-genai`, no el paquete `google-generativeai` legacy
  y deprecado)
- Tests: pytest (carpeta `tests/unit/` y `tests/integration/`, aún sin implementar)

## Arquitectura — hexagonal liviana

```
src/app/
├── domain/           # entidades y PUERTOS (ABC + @abstractmethod). Sin dependencias externas.
├── application/       # casos de uso — orquestan domain, reciben puertos por constructor
├── infrastructure/    # implementaciones concretas de los puertos (DB, LLMs, seguridad)
└── api/               # FastAPI routers y schemas Pydantic
```

Reglas:
- `application/` NUNCA importa clases concretas de `infrastructure/` — solo puertos de
  `domain/ports/`. Ejemplo de referencia: `ProductService` recibe `ProductRepositoryPort`
  en el constructor, nunca instancia `ProductRepository` directamente.
- Todo repositorio nuevo sigue el patrón: puerto (`domain/ports/xxx_port.py`) →
  implementación (`infrastructure/db/xxx_repository.py`, hereda del puerto) → service
  (`application/xxx_service.py`, recibe el puerto por constructor).
- Errores de negocio usan las excepciones de `core/exceptions.py` (`AppException` y
  subclases), nunca `HTTPException` suelta en el router ni `ValueError` genérico en
  application/. Los handlers globales en `core/error_handlers.py` las capturan y devuelven
  el formato estándar `{"error": {"code": ..., "message": ...}}`.

## Convenciones de nombres

- Todo en inglés: `ProductService`, no `ProductoService`. `hashed_password`, no `password`
  (el nombre debe dejar explícito que es un hash, nunca guardar contraseñas en texto plano).
- Archivos de puertos: `xxx_repository_port.py`. Implementaciones: `xxx_repository.py`.

## Git / GitHub

- Ramas: `<tipo>/issue-<número>-<slug-corto>`, donde `<tipo>` viene de la label del issue
  (`feat`, `refactor`, `ops`, `docs`). Ej: `feat/issue-6-langchain-router`.
- PRs: usar el template en `.github/PULL_REQUEST_TEMPLATE.md`. La línea `Closes #N` va
  siempre en **inglés** (no "Cierra #N" — GitHub solo reconoce las keywords en inglés para
  auto-cerrar issues).
- `main` tiene branch protection: requiere PR + CI en verde antes de poder mergear. No
  intentar push directo a `main`.
- Antes de abrir el PR: correr `uv run ruff check . --fix` y confirmar que no rompe nada.

## CI

`.github/workflows/ci.yml` corre lint (ruff) y un smoke test (`from app.main import app`)
en cada push/PR. Si agregás una dependencia nueva que se usa a nivel de import (no solo
dentro de funciones), verificá que el smoke test del CI tenga las env vars dummy necesarias
(ver `DATABASE_URL` como ejemplo — el CI no tiene una DB real corriendo).

## Seguridad

- Nunca commitear `.env` ni secretos reales. `.env.example` documenta las variables sin
  valores reales.
- Al agregar cualquier feature de LLM, considerar el OWASP Top 10 for LLM Applications
  (prompt injection, excessive agency) — hay un checklist planeado en el issue #27.
- Los agentes NO deberían acceder a herramientas fuera de su rol (ej: el agente de Soporte
  no debería poder crear/modificar órdenes).

## Qué NO hacer sin preguntar primero

- No agregar campos a modelos (ej: DNI, edad) sin una necesidad funcional concreta —
  evitar recolectar datos personales sensibles sin justificación.
- No mezclar refactors grandes (reorganizar archivos) con features en el mismo PR.
- No agregar roles/permisos, auditoría, u otras features "por si acaso" sin que estén
  en un issue — anotarlas como issues nuevos en su lugar.