# syntax=docker/dockerfile:1

# =============================================================================
# Issue #18 — Imagen multi-stage para FastAPI (web) + Celery (worker).
#
# La MISMA imagen sirve para los dos procesos; el comando se sobrescribe en
# `docker run` (ver AGENTS.md).
#
# Build stage: instala dependencias con uv. Ninguna dependencia necesita
# compilarse (todas traen wheels: psycopg[binary], argon2/bcrypt, onnxruntime,
# etc.), así que no hacen falta compiladores acá. uv es un binario estático que
# se trae de su imagen oficial y NO queda en la imagen final.
# =============================================================================

FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# copy: uv copia (no hardlinkea) los paquetes, para que el .venv sea autocontenido
# y se pueda copiar entre stages sin romper symlinks.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Solo dependencias (el proyecto se instala editable abajo). Se copia
# pyproject/uv.lock (y README.md, que hatchling necesita para buildear) primero
# para cachear la capa de deps.
COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Proyecto en modo editable (apunta a /app/src): así `import app` funciona tanto
# para el worker de Celery (que no usa `--app-dir src`) como para la API, y se
# preserva el layout `src/app/...` que espera `chromadb_adapter._PROJECT_ROOT`.
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev


# =============================================================================
# Runtime stage: solo lo necesario para correr.
# =============================================================================

FROM python:3.12-slim

# libgomp1: la requiere onnxruntime (dependencia de chromadb) en Debian slim.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Usuario no-root dedicado (UID/GID fijos para consistencia).
RUN groupadd --gid 1001 app \
    && useradd --uid 1001 --gid app --home-dir /app --create-home app

WORKDIR /app

# venv + código, desde el build stage (sin uv, sin compiladores, sin secrets).
COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --chown=app:app src ./src

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER app

EXPOSE 8000

# Por defecto: API web. El worker se arranca sobrescribiendo el comando:
#   docker run ... ia-store celery -A app.infrastructure.tasks.celery_app:celery_app worker --loglevel=info
CMD ["uvicorn", "app.main:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000"]
