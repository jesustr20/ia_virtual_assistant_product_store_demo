# Seguridad — secretos y dependencias

> **Checklist OWASP Top 10 for LLM Applications (2026)** aplicado al proyecto: ver
> [`OWASP_LLM_CHECKLIST.md`](OWASP_LLM_CHECKLIST.md) (issue #27). Este archivo cubre
> secretos, dependencias y la imagen Docker; el checklist cubre los riesgos específicos
> de LLM.

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

## Dependencias vulnerables (escaneo en CI)

`pip-audit` corre en el workflow de CI (`.github/workflows/ci.yml`), después del lint y
antes de pytest. **Falla ante cualquier vulnerabilidad** encontrada; no soporta filtrar
por severidad, así que los hallazgos conocidos sin fix se allowlistean con `--ignore-vuln`
y su motivo queda documentado en el comentario de ese step de CI.

Cuando aparece una alerta nueva:

1. Mirá el ID de la vulnerabilidad y el paquete que reporta el CI.
2. Corré en local `uv run pip-audit --skip-editable` para ver el detalle y si trae
   `fix_versions`.
3. **Si hay fix**: subí la dependencia en `pyproject.toml` (`uv add <paquete>@<versión>`),
   corré `uv lock`, y verificá que el step quede en verde.
4. **Si no hay fix** (o rompe algo): allowlisteá el ID con `--ignore-vuln` y una razón
   escrita en el comentario del step de CI, y abrí un issue para trackearlo —no acumular
   ignores sin revisar.

Dependabot alerts complementa esto: avisa por UI/email aunque el CI no llegue a fallar.

### Hallazgos actuales (chromadb 1.5.9) y análisis de riesgo por CVE

El único paquete reportado hoy es `chromadb` (1.5.9, la **última** versión publicada: los
4 hallazgos tienen `fix_versions: []`, así que no hay parche disponible).

**Nota sobre el conteo "5 vs 4".** El output de `pip-audit --skip-editable` dice
`Found 5 known vulnerabilities in 1 package`, pero en realidad son **4 IDs únicos**:
`PYSEC-2026-311` aparece **duplicado** en la base OSV/PYSEC (dos entradas de advisory que
mapean al mismo `CVE-2026-45829`), así que se lista dos veces:

```
Name     Version ID              Fix Versions
-------- ------- --------------- ------------
chromadb 1.5.9   PYSEC-2026-311
chromadb 1.5.9   PYSEC-2026-311   <- duplicado del mismo CVE
chromadb 1.5.9   PYSEC-2026-3814
chromadb 1.5.9   PYSEC-2026-3815
chromadb 1.5.9   PYSEC-2026-3813
```

Un único `--ignore-vuln PYSEC-2026-311` cubre las dos filas, por eso el CI allowlistea 4
IDs y el resumen "5 ignored" se refiere a 5 filas, no a 5 vulnerabilidades distintas.

**Contexto de despliegue relevante para el análisis.** El proyecto usa ChromaDB en modo
cliente/servidor (`chromadb.HttpClient`) **sin habilitar autenticación** (no se configuran
`CHROMA_SERVER_AUTHN_PROVIDER` ni `CHROMA_SERVER_AUTHN_CREDENTIALS`), y en
`docker-compose.yml` el servicio `chroma` **no expone su puerto al host** (no hay entrada
`ports:`, solo lo alcanzan `api`/`worker` por la red interna de Docker). Los embeddings son
de Gemini (`GoogleGenerativeAIEmbeddings`), nunca un model repository remoto ni
`trust_remote_code`. Todo esto cambia qué tan explotable es cada CVE en *este* proyecto.

| ID | CVE | Clase | Requiere para explotar | ¿Mitigado por la topología? |
|---|---|---|---|---|
| `PYSEC-2026-311` | CVE-2026-45829 | Code injection **pre-auth** (≥1.0.0) | Red hacia el HTTP API de Chroma **sin credenciales** + enviar un model repository malicioso con `trust_remote_code=true` a `/api/v2/tenants/{tenant}/databases/{db}/collections` | **Sí, parcialmente**: no hay ruta desde internet a Chroma (sin `ports:`). Queda explotable desde cualquier cosa que ya esté dentro de la red interna (api/worker comprometidos, SSRF). |
| `PYSEC-2026-3814` | CVE-2026-45833 | Code injection **autenticado** (≥0.4.17) | Usuario autenticado + permiso `UPDATE_COLLECTION` + model repo malicioso con `trust_remote_code=true` | No aplica hoy: sin auth de Chroma no existe superficie "autenticada". Relevante si se habilita auth/RBAC. |
| `PYSEC-2026-3815` | CVE-2026-45831 | RBAC cross-tenant (≥0.5.0) | `SimpleRBACAuthorizationProvider` habilitado + usuario autenticado | No aplica hoy: el proyecto no usa RBAC ni multi-tenant. Relevante si se habilita. |
| `PYSEC-2026-3813` | CVE-2026-45830 | Falta de autorización (≥0.4.17) | Usuario autenticado para leer/escribir/borrar en cualquier tenant | No aplica hoy: sin auth no hay tenants aislados que cruzar. Relevante si se habilita auth/multi-tenant. |

**Análisis por CVE (no alcanza con "no hay fix, ignorado"):**

- **CVE-2026-45829 (`PYSEC-2026-311`, pre-auth, CVSS 4.0 crítico `PR:N`)** — el más serio.
  Explotable **sin credenciales** por cualquiera que alcance el HTTP API de Chroma. El
  "puerto no expuesto al host" **reduce materialmente** la explotabilidad: un atacante
  externo no tiene camino de red directo. Pero **no la elimina**: el riesgo residual es
  que un compromiso previo de `api` o `worker` (RCE vía otro bug, SSRF, o un pivote desde
  la superficie de prompt-injection que cubre el issue #27) dé acceso a la red interna y,
  desde ahí, RCE directo en el contenedor de Chroma. Como además Chroma corre **sin
  autenticación**, no hay una segunda barrera: el aislamiento de red es la ÚNICA defensa.
- **CVE-2026-45833 (`PYSEC-2026-3814`)** — inyección de código pero requiere un usuario
  **autenticado** con `UPDATE_COLLECTION`. Este proyecto no habilita auth de Chroma, así
  que hoy no hay superficie autenticada que explotar. Ojo: esto **no es una mitigación**,
  es un síntoma de que no hay auth en absoluto; la clase "inyección vía model repository +
  `trust_remote_code`" ya queda cubierta por el CVE pre-auth (PYSEC-2026-311) mientras no
  haya auth. Si más adelante se habilita auth/RBAC, este CVE pasa a ser relevante.
- **CVE-2026-45831 (`PYSEC-2026-3815`)** — bug del `SimpleRBACAuthorizationProvider` que
  no valida a qué tenant/db/collection aplica un permiso. Requiere RBAC habilitado. El
  proyecto no usa RBAC ni multi-tenant, así que hoy es no alcanzable. Riesgo futuro
  condicionado a adoptar auth multi-tenant.
- **CVE-2026-45830 (`PYSEC-2026-3813`)** — falta de validación de autorización: cualquier
  usuario autenticado puede leer/escribir/borrar en colecciones de otros tenants. Igual
  que el anterior: sin auth, no hay superficie; relevante solo si se habilita auth y hay
  más de un tenant.

**Riesgo residual neto.** Con el deploy actual (`docker-compose.yml`), el único hallazgo
con exposición real es **CVE-2026-45829**, y su explotabilidad depende de que un atacante
ya haya comprometido un contenedor interno o logre un SSRF hacia Chroma: pasa de "RCE
remoto sin credenciales desde internet" a "RCE posterior a un compromiso interno". Los
otros tres son no alcanzables hoy por la ausencia de auth/RBAC, no por una mitigación
deliberada. La deuda real del proyecto es **operar Chroma sin autenticación**: mientras
siga así, toda la seguridad de Chroma descansa en el aislamiento de red. Acciones a
trackear (sin mezclarlas en este PR):

- Subir `chromadb` ni bien publique una versión parcheada (hay issue abierto para
  trackearlo) y quitar el `--ignore-vuln` correspondiente.
- Evaluar habilitar autenticación por token en Chroma incluso en la red interna (defensa
  en profundidad) — como issue nuevo, no acá.
- Nunca exponer el puerto de Chroma al host; si hace falta debuggear, usar
  `docker compose exec chroma`.
- Tratar CVE-2026-45829 como insumo del checklist OWASP para LLM (#27): la vía de
  prompt-injection sobre `api` es el camino de pivote más plausible hacia Chroma.

## Escaneo de la imagen Docker (issue #26)

### Herramienta elegida: Trivy (no docker scout)

`docker scout` no está disponible en este entorno (no hay plugin instalado; `docker scout`
da "unknown command" y solo existen los plugins `buildx`, `compose` y `model`). Trivy es
open source, no requiere suscripción ni Docker Desktop, escanea **tanto** los paquetes OS
del base image **como** las dependencias Python del `.venv`, y se puede correr sin
instalación local (`docker run aquasec/trivy`) o como binario estático (acá se usó
`trivy v0.74.0`). Es además la opción más fácil de integrar a CI más adelante
(`aquasecurity/trivy-action`). Por eso se eligió Trivy.

Comando: `trivy image --scanners vuln ia-store:test` (imagen buildeada con
`docker build -t ia-store:test .`).

### Resultados reales (antes del endurecimiento)

| Objetivo | Total | CRITICAL | HIGH | MEDIUM | LOW | Observación |
|---|---|---|---|---|---|---|
| Base image `python:3.12-slim` (Debian 13.7) | 150 | 0 | 44 | 49 | 57 | Los 44 HIGH colapsan en **8 CVEs únicos**; sin versión parcheada en Debian 13.7 a la fecha. |
| Python (`.venv`) | 10 | 2 | 2 | 5 | 1 | 4 de chromadb (ya analizados en #25) + 6 de pip. |

Los 2 CRITICAL y 2 HIGH de Python son exactamente los **4 CVEs de chromadb** que ya
documentó la sección anterior (issue #25): `CVE-2026-45829`/`-45833`/`-45830`/`-45831`.
No se repite el análisis acá; ver "Hallazgos actuales (chromadb 1.5.9)" más arriba. Trivy
los califica igual que NVD (2 CRITICAL, 2 HIGH), y el análisis de mitigación por topología
de red sigue valiendo.

### Hallazgos NUEVOS (no cubiertos por #25)

**pip (6 CVEs: 5 MEDIUM, 1 LOW).** Provienen del Python **de sistema** que trae
`python:3.12-slim` (`pip 25.0.1` en `/usr/local/lib/python3.12/site-packages`), **no** del
`.venv` de la app. La app corre desde `/app/.venv` (que no incluye pip), así que ese pip
es superficie muerta: nunca se ejecuta. Los 6 tenían `fix_versions` disponibles (25.3+).
**Mitigación aplicada:** se elimina pip del Python de sistema en el Dockerfile, lo que
borra los 6 hallazgos (10 → 4 en Python).

**Paquetes OS del base image (44 HIGH → 8 CVEs únicos).** La imagen base Debian 13.7 trae
paquetes estándar que NVD cataloga HIGH por CVSS genérico, pero que no son alcanzables en
este contenedor por diseño:

| CVE(s) | Paquete | Requiere para explotar | ¿Mitigado acá? |
|---|---|---|---|
| `CVE-2026-76642`, `-78408`, `-78409`, `-78410` | util-linux (`mount`/`nsenter`/`unshare`) | Binarios setuid de `mount` + `CAP_SYS_ADMIN` para montar / hooks `X-mount` privilegiados | **Sí**: usuario no-root (UID 1001), sin `CAP_SYS_ADMIN`, y se **quitaron los bits setuid/setgid** en el Dockerfile. |
| `CVE-2025-69720` | ncurses (`libncursesw6`/`libtinfo6`) | Desbordamiento de buffer vía entrada de terminal interactiva | **Sí**: la app no tiene TUI/terminal interactivo. |
| `CVE-2026-16742` | systemd (`libsystemd0`/`libudev1`) | `systemd-homed` corriendo (privilege escalation local) | **Sí**: no corre `systemd-homed` dentro del contenedor. |
| `CVE-2026-54369` | acl (`libacl1`) | Proceso privilegiado usando `libacl` sobre rutas controladas por el atacante | **Sí**: la app no invoca `libacl` sobre rutas atacables. |
| `CVE-2026-9538` | perl-base (`Archive::Tar`) | Procesar archivos `.tar` con `perl`/`Archive::Tar` | **Sí**: la app no descomprime tars con perl. |

**Riesgo residual neto (OS).** Estos 8 CVEs no tienen parche publicado en Debian 13.7
todavía (`fixed=None` en Trivy), así que un `docker build --pull` hoy **no** los elimina
del reporte (sí conviene correrlo periódicamente para tomar los fixes de Debian cuando
salgan). La mitigación real es que el contenedor no tiene ni los privilegios
(`CAP_SYS_ADMIN`, setuid) ni los binarios/caminos de ejecución que esos CVEs necesitan.
El riesgo residual honesto: si un atacante lograra un **escape del contenedor** (bug de
kernel/runtime) o elevación a root dentro del contenedor, algunos (ej. los de util-linux)
volverían a ser relevantes; por eso el objetivo de fondo es **no llegar a ese punto**
(usuario no-root, setuid limpio, base mínima).

### Endurecimiento aplicado en este issue

1. **Quitar pip/setuptools del Python de sistema** (superficie muerta + 6 CVEs).
2. **Quitar bits setuid/setgid** de los binarios del base image (`mount`, `umount`, `su`,
   `passwd`, `chsh`, `chfn`, `newgrp`, `gpasswd`, `unix_chkpwd`, `expiry`, `chage`, …).
   En un contenedor no-root no se necesitan y son la vía de entrada de los CVEs de
   util-linux/shadow/acl.
3. Lo ya logrado en #18 se mantiene: usuario no-root `app` (UID 1001), base
   `python:3.12-slim`, multi-stage sin secretos/`.env` en la imagen.

Resultado tras el endurecimiento: Python pasa de 10 a 4 hallazgos (solo chromadb). El OS
sigue reportando 150 porque Trivy reporta a nivel de **paquete** y no puede ver que los
bits setuid se quitaron; la reducción es de *explotabilidad*, no de *reporte*.

### Recomendaciones para trackear (no en este PR)

- Integrar el escaneo de imagen a CI (step de `aquasecurity/trivy-action` o
  `docker run aquasec/trivy`) para que no se haga solo a mano — issue nuevo.
- Rebuildear la imagen con `docker build --pull` de forma periódica para tomar los fixes
  de Debian de los 8 CVEs OS en cuanto salgan.
- **Read-only root filesystem**: factible en principio — el código de la app no escribe
  a disco (verificado: no hay `open(...,'w')`/`write_text`/`tempfile` en `src/`); si se
  habilita (`read_only: true` + `tmpfs` para `/tmp`), conviene probar API y worker.
- **HEALTHCHECK** en el Dockerfile: posible pero requiere un check basado en Python
  (la imagen slim no trae `curl`/`wget`); opcional.
- Verificación: la imagen sigue buildeando y corriendo (uvicorn arranca
  "Application startup complete" y el worker de Celery levanta; ver PR).
