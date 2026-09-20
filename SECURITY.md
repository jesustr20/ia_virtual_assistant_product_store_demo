# Seguridad — gestión de secretos

## Principios

- Los secretos viven **solo en `.env`**, que está en `.gitignore` y **nunca se commitea**.
- Nunca se hardcodea un secreto, API key o contraseña en el código: todo se lee vía
  `os.getenv(...)` / `os.environ.get(...)` (ver `src/app/`).
- `.env.example` documenta las variables necesarias **sin valores reales**; es la
  referencia para armar un `.env` nuevo (`cp .env.example .env` y completar).

## Detección automática (ya habilitada a nivel de repo)

- **GitHub secret scanning** y **push protection** están habilitados en la configuración
  del repositorio. Push protection bloquea commits que contengan patrones de secretos
  conocidos antes de que lleguen al remoto.
- **Dependabot alerts** está habilitado para avisar de dependencias vulnerables.
- Estos controles son defensa en profundidad: la primera línea sigue siendo no commitear
  `.env` ni hardcodear secretos.

## Variables de entorno

| Variable | Uso | Fuente para rotar/regenerar |
|---|---|---|
| `GEMINI_API_KEY` | LLM (router + agente de catálogo) y embeddings de ChromaDB | Google AI Studio |
| `SECRET_KEY` | Firma de tokens JWT | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `DATABASE_URL` | Conexión a PostgreSQL (incluye credenciales de la DB) | Proveedor/instancia de PostgreSQL |
| `REDIS_URL` | Cache y broker de Celery | Instancia de Redis |
| `CELERY_BROKER_URL` | Broker de Celery (por defecto cae a `REDIS_URL`) | Instancia de Redis |
| `CHROMA_HOST` / `CHROMA_PORT` | Servidor de ChromaDB (no es secreto, pero va en `.env`) | — |
| `SENTRY_DSN` | Error tracking (opcional) | Panel de Sentry |

## Proceso de rotación si un secreto se filtra

Si un secreto se expone por error (commit, leak, compartido), **no alcanza con borrarlo
del repo**: hay que revocarlo en su origen y rotarlo, porque un bot pudo copiarlo en
minutos. Pasos:

1. **Revocá/regenerá la key en su origen** según el tipo:
   - `GEMINI_API_KEY` → Google AI Studio (creá una key nueva y revocá la vieja).
   - `SENTRY_DSN` → panel de Sentry (rotá/revocá el DSN del proyecto).
   - `SECRET_KEY` → regenerá con
     `python -c "import secrets; print(secrets.token_hex(32))"`.
     Ojo: rotar `SECRET_KEY` invalida todos los JWT emitidos (los usuarios vuelven a
     loguearse).
   - Contraseña de la DB → cambiala en el proveedor de PostgreSQL y actualizá
     `DATABASE_URL` en `.env` con las credenciales nuevas.
2. **Actualizá `.env`** con el/los valor/es nuevos.
3. **Reiniciá los servicios que leen esos secretos.** Tanto la API web como el worker de
   Celery leen las variables al arrancar / al importar los módulos, así que hay que
   reiniciar **ambos procesos**:
   ```bash
   # API
   uv run uvicorn app.main:app --app-dir src --reload
   # Worker de Celery
   uv run celery -A app.infrastructure.tasks.celery_app:celery_app worker --loglevel=info
   ```
   (En producción/Docker: reconstruir o reiniciar los contenedores `api` y `worker`.)
4. **Investigá** si la key filtrada se usó de forma indebida (ej. consumo anómalo de la
   API de Gemini, accesos no autorizados) y revocá cualquier token/sesión comprometida.
5. **Corregí la causa** (eliminá el secreto del historial de git si se commiteó, con
   `git filter-repo` o rehaciendo el repo si es un portfolio) y avisá a los responsables.
