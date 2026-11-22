#!/bin/bash
# ==========================================
# Proyecto final
# Ejecutor de pruebas k6 (Bash)
# ==========================================

set -e

echo "Iniciando prueba de carga con k6..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

docker run --rm -i \
  --network proyecto-final-devops_devops-lab-net \
  -e TARGET_URL="http://nginx" \
  grafana/k6:0.56.0 run - < "${SCRIPT_DIR}/load-test.js"
