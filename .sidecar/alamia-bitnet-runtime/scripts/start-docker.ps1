$ErrorActionPreference = "Stop"
Write-Host "Starting Alamia BitNet Runtime Docker sidecar..." -ForegroundColor Cyan
docker compose -f "$PSScriptRoot\..\docker-compose.yml" up -d
Write-Host "[OK] BitNet sidecar started on port 8080." -ForegroundColor Green
