#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# scaffold_structure.sh
#
# Crea la nueva estructura hexagonal-liviana y mueve (git mv)
# los archivos existentes a su nueva ubicación.
#
# Correr DESDE LA RAIZ del repo clonado.
# Requiere: estar en un repo git limpio (sin cambios sin commitear)
# ============================================================

if [ ! -d ".git" ]; then
  echo "❌ Este script debe correrse desde la raíz del repo (no se encontró .git)"
  exit 1
fi

if [ -n "$(git status --porcelain)" ]; then
  echo "⚠️  Tenés cambios sin commitear. Commiteá o guardá (git stash) antes de continuar."
  exit 1
fi

echo "📁 Creando estructura de carpetas..."

mkdir -p src/app/core
mkdir -p src/app/api/routes
mkdir -p src/app/api/schemas
mkdir -p src/app/domain/entities
mkdir -p src/app/domain/ports
mkdir -p src/app/application
mkdir -p src/app/infrastructure/db
mkdir -p src/app/infrastructure/llm
mkdir -p src/app/infrastructure/memory
mkdir -p tests/unit
mkdir -p tests/integration
mkdir -p docs
mkdir -p scripts

# __init__.py en cada paquete nuevo
for dir in \
  src/app src/app/core src/app/api src/app/api/routes src/app/api/schemas \
  src/app/domain src/app/domain/entities src/app/domain/ports \
  src/app/application src/app/infrastructure src/app/infrastructure/db \
  src/app/infrastructure/llm src/app/infrastructure/memory \
  tests tests/unit tests/integration
do
  touch "$dir/__init__.py"
done

echo "🚚 Moviendo archivos existentes con git mv..."

git mv app/main.py src/app/main.py
git mv app/db.py src/app/infrastructure/db/session.py
git mv app/models.py src/app/infrastructure/db/models.py
git mv app/repositories.py src/app/infrastructure/db/product_repository.py
git mv app/schemas.py src/app/api/schemas/product_schemas.py
git mv app/endpoints/ai_endpoints.py src/app/api/routes/ai_routes.py
git mv app/endpoints/product_endpoints.py src/app/api/routes/product_routes.py
git mv app/services/gemini_service.py src/app/infrastructure/llm/gemini_adapter.py
git mv app/services/session_memory.py src/app/infrastructure/memory/session_memory.py

# Estos dos quedan temporalmente en application/ hasta revisar su contenido
# y decidir si van a domain/, application/ o se dividen entre ambos.
git mv app/services/ai_handler.py src/app/application/ai_handler_TEMP.py
git mv app/services/product_service.py src/app/application/product_service_TEMP.py

# Limpiar carpetas viejas ya vacías
rmdir app/endpoints app/services app 2>/dev/null || true

echo ""
echo "✅ Estructura creada y archivos movidos."
echo "⚠️  Revisá los imports rotos (ej: 'from app.services.gemini_service import ...')"
echo "    ahora van a apuntar a las nuevas rutas."
echo "⚠️  Los archivos *_TEMP.py en application/ necesitan revisión manual:"
echo "    decidir si van a domain/, application/, o se dividen."
echo ""
echo "📌 Recordá poner github_issues.json y create_issues.sh dentro de scripts/"
echo "   (descargados por separado, no vienen incluidos en este script)."
echo ""
echo "Próximo paso: git status para revisar, después git commit."
