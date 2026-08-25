$ErrorActionPreference = "Stop"
Write-Host "Stopping Alamia BitNet Runtime Docker sidecar..." -ForegroundColor Yellow
docker compose -f "$PSScriptRoot\..\docker-compose.yml" down
Write-Host "[OK] BitNet sidecar stopped." -ForegroundColor Green
