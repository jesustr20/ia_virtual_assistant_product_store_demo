#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# create_issues.sh
#
# Crea los 21 issues del proyecto en el repo de GitHub actual,
# leyendo su definicion desde github_issues.json (mismo directorio).
#
# Requisitos:
#   1. Tener GitHub CLI instalado: https://cli.github.com
#   2. Estar logueado:  gh auth login
#   3. Ejecutar este script DESDE ADENTRO del repo local
#      (gh detecta automaticamente a que repo de GitHub subir)
#   4. Tener jq instalado (para parsear el JSON)
#
# Uso:
#   chmod +x create_issues.sh
#   ./create_issues.sh
# ============================================================

JSON_FILE="${1:-$(dirname "$0")/github_issues.json}"

if ! command -v gh &> /dev/null; then
  echo "❌ GitHub CLI (gh) no está instalado. Instalalo desde https://cli.github.com"
  exit 1
fi

if ! command -v jq &> /dev/null; then
  echo "❌ jq no está instalado. Instalalo con: sudo apt install jq"
  exit 1
fi

if ! gh auth status &> /dev/null; then
  echo "❌ No estás logueado en gh. Corré primero: gh auth login"
  exit 1
fi

if [ ! -f "$JSON_FILE" ]; then
  echo "❌ No se encontró $JSON_FILE"
  exit 1
fi

echo "🔎 Repo detectado: $(gh repo view --json nameWithOwner -q .nameWithOwner)"
echo ""

# --- Paso 1: crear los labels necesarios (si no existen ya) ---
echo "📌 Creando labels con colores (se ignoran los que ya existen)..."

# Mapa de colores por label. Default gris si no está en la lista.
color_for_label() {
  case "$1" in
    refactor)   echo "d4c5f9" ;;  # violeta claro
    feat)       echo "0e8a16" ;;  # verde
    ops)        echo "1d76db" ;;  # azul
    docs)       echo "5319e7" ;;  # violeta oscuro
    fase-1|fase-2|fase-3|fase-4|fase-5|fase-6) echo "c5def5" ;;  # celeste
    suave)      echo "0e8a16" ;;  # verde
    intermedio) echo "1d76db" ;;  # azul
    dificil)    echo "f66a0a" ;;  # naranja
    critico)    echo "b60205" ;;  # rojo
    *)          echo "ededed" ;;  # gris default
  esac
}

LABELS=$(jq -r '.[].labels[]' "$JSON_FILE" | sort -u)
for label in $LABELS; do
  color=$(color_for_label "$label")
  gh label create "$label" --color "$color" --force && echo "  + $label ($color)"
done
echo ""

# --- Paso 2: crear los issues ---
TOTAL=$(jq 'length' "$JSON_FILE")
echo "🚀 Creando $TOTAL issues..."
echo ""

for i in $(seq 0 $((TOTAL - 1))); do
  TITLE=$(jq -r ".[$i].title" "$JSON_FILE")
  BODY=$(jq -r ".[$i].body" "$JSON_FILE")
  LABELS_CSV=$(jq -r ".[$i].labels | join(\",\")" "$JSON_FILE")

  echo "  -> $TITLE"
  gh issue create --title "$TITLE" --body "$BODY" --label "$LABELS_CSV" > /dev/null
done

echo ""
echo "✅ Listo. Los $TOTAL issues fueron creados en GitHub."
echo "   Revisalos en: $(gh repo view --json url -q .url)/issues"
