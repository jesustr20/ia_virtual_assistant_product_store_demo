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

# Endurecimiento (issue #26): quitar pip del Python de sistema. `python:3.12-slim`
# lo trae por defecto, pero la app corre desde /app/.venv, así que el pip de
# sistema es superficie de ataque muerta (trivy reporta CVEs de pip sobre él).
RUN rm -rf /usr/local/lib/python3.12/site-packages/pip* \
           /usr/local/lib/python3.12/site-packages/setuptools*

# Endurecimiento (issue #26): quitar los bits setuid/setgid de los binarios del base
# image que la app no usa (mount, umount, su, passwd, chsh, chfn, newgrp, gpasswd,
# etc.). En un contenedor no-root no son necesarios y son la vía de entrada de los
# CVEs de util-linux/shadow/acl que reporta el escaneo. `find` es más robusto que
# listar binarios a mano ante cambios de la imagen base.
RUN find / -xdev -type f \( -perm -4000 -o -perm -2000 \) -exec chmod -s {} + 2>/dev/null || true

# Usuario no-root dedicado (UID/GID fijos para consistencia).
RUN groupadd --gid 1001 app \
    && useradd --uid 1001 --gid app --home-dir /app --create-home app

WORKDIR /app

# venv + código, desde el build stage (sin uv, sin compiladores, sin secrets).
COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --chown=app:app src ./src

# Alembic (migraciones) — se corre `alembic upgrade head` al arrancar el api en
# docker-compose.
COPY --chown=app:app alembic.ini ./
COPY --chown=app:app alembic ./alembic

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER app

EXPOSE 8000

# Por defecto: API web. El worker se arranca sobrescribiendo el comando:
#   docker run ... ia-store celery -A app.infrastructure.tasks.celery_app:celery_app worker --loglevel=info
CMD ["uvicorn", "app.main:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000"]
