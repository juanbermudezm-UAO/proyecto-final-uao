# ==========================================
# Proyecto final
# Ejecutor de pruebas k6 (PowerShell)
# ==========================================

Write-Host "Iniciando prueba de carga con k6..." -ForegroundColor Cyan

Get-Content "$PSScriptRoot/load-test.js" | docker run --rm -i `
  --network proyecto-final-devops_devops-lab-net `
  -e TARGET_URL="http://nginx" `
  grafana/k6:0.56.0 run -
