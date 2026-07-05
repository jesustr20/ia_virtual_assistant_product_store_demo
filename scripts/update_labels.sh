#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# update_labels.sh
#
# Para usar SOLO SI YA corriste create_issues.sh antes (issues
# ya existen en GitHub). Este script:
#   1. Actualiza el color de todos los labels usados
#   2. Agrega la label de dificultad (suave/intermedio/dificil/critico)
#      a cada issue existente, matcheando por título exacto
#
# NO crea issues nuevos, así que es seguro correrlo aunque
# ya hayas corrido create_issues.sh antes.
#
# Requisitos: gh, jq — mismos que create_issues.sh
# ============================================================

JSON_FILE="$(dirname "$0")/github_issues.json"

if ! gh auth status &> /dev/null; then
  echo "❌ No estás logueado en gh. Corré: gh auth login"
  exit 1
fi

echo "🔎 Repo detectado: $(gh repo view --json nameWithOwner -q .nameWithOwner)"
echo ""

# --- Paso 1: actualizar colores de labels (idempotente, --force) ---
color_for_label() {
  case "$1" in
    refactor)   echo "d4c5f9" ;;
    feat)       echo "0e8a16" ;;
    ops)        echo "1d76db" ;;
    docs)       echo "5319e7" ;;
    fase-1|fase-2|fase-3|fase-4|fase-5|fase-6) echo "c5def5" ;;
    suave)      echo "0e8a16" ;;
    intermedio) echo "1d76db" ;;
    dificil)    echo "f66a0a" ;;
    critico)    echo "b60205" ;;
    *)          echo "ededed" ;;
  esac
}

echo "📌 Actualizando colores de labels..."
LABELS=$(jq -r '.[].labels[]' "$JSON_FILE" | sort -u)
for label in $LABELS; do
  color=$(color_for_label "$label")
  gh label create "$label" --color "$color" --force > /dev/null
  echo "  + $label ($color)"
done
echo ""

# --- Paso 2: traer todos los issues actuales del repo (número + título) ---
echo "📥 Descargando lista de issues actuales del repo..."
gh issue list --state all --limit 200 --json number,title > /tmp/_current_issues.json
echo ""

# --- Paso 3: por cada issue del JSON, buscar su número por título exacto
#             y agregarle SOLO la label de dificultad (última del array) ---
TOTAL=$(jq 'length' "$JSON_FILE")
echo "🏷️  Agregando labels de dificultad a los $TOTAL issues existentes..."
echo ""

for i in $(seq 0 $((TOTAL - 1))); do
  TITLE=$(jq -r ".[$i].title" "$JSON_FILE")
  DIFFICULTY=$(jq -r ".[$i].labels[-1]" "$JSON_FILE")

  NUMBER=$(jq -r --arg t "$TITLE" '.[] | select(.title == $t) | .number' /tmp/_current_issues.json)

  if [ -z "$NUMBER" ]; then
    echo "  ⚠️  No encontré un issue con título exacto: $TITLE (saltado)"
    continue
  fi

  gh issue edit "$NUMBER" --add-label "$DIFFICULTY" > /dev/null
  echo "  -> #$NUMBER: +$DIFFICULTY"
done

echo ""
echo "✅ Listo. Revisá los labels en: $(gh repo view --json url -q .url)/issues"
