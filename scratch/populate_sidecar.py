import os
from pathlib import Path

sidecar_dir = Path(".sidecar/alamia-bitnet-runtime")
sidecar_dir.mkdir(parents=True, exist_ok=True)
(sidecar_dir / "bin").mkdir(exist_ok=True)
(sidecar_dir / "scripts").mkdir(exist_ok=True)

# 1. docker-compose.yml
docker_compose_content = """services:
  bitnet-server:
    image: mcr.microsoft.com/appsvc/docs/sidecars/sample-experiment:bitnet-b1.58-2b-4t-gguf
    container_name: bitnet-server
    restart: unless-stopped
    ports:
      - "${BITNET_HOST_PORT:-8080}:11434"
    volumes:
      - ../../models:/models:ro
    environment:
      - SLM_PORT=11434
      - WEBSITE_SLM_STARTUP_ARGUMENTS=-t ${BITNET_THREADS:-4} --repeat-penalty ${BITNET_REPEAT_PENALTY:-1.15} --repeat-last-n 64 --top-p ${BITNET_TOP_P:-0.9} --min-p ${BITNET_MIN_P:-0.05} --temp ${BITNET_TEMP:-0.7} -c ${BITNET_CTX_SIZE:-4096} --parallel ${BITNET_PARALLEL:-2}
    healthcheck:
      test: ["CMD-SHELL", "wget -q --spider http://localhost:11434/health || exit 1"]
      interval: 15s
      timeout: 5s
      retries: 3
      start_period: 10s
"""
(sidecar_dir / "docker-compose.yml").write_text(docker_compose_content, encoding="utf-8")

# 2. .env.example
env_example = """BITNET_HOST_PORT=8080
BITNET_THREADS=4
BITNET_TEMP=0.7
BITNET_TOP_P=0.9
BITNET_MIN_P=0.05
BITNET_REPEAT_PENALTY=1.15
BITNET_CTX_SIZE=4096
BITNET_PARALLEL=2
"""
(sidecar_dir / ".env.example").write_text(env_example, encoding="utf-8")
if not (sidecar_dir / ".env").exists():
    (sidecar_dir / ".env").write_text(env_example, encoding="utf-8")

# 3. start-portable.ps1
start_portable_ps1 = """<#
.SYNOPSIS
Portable BitNet Server Launcher for Windows (Zero Docker Required).
Launches Microsoft BitNet via precompiled native AVX2 llama-server.exe.
#>
$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " Starting Alamia BitNet Runtime (Windows Native / Zero Docker)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$port = 8080
$threads = [Math]::Max(1, [Environment]::ProcessorCount - 2)
$exePath = Join-Path $PSScriptRoot "bin\\llama-server.exe"

# Search for model weights in central models folder or local
$modelCandidates = @(
    (Join-Path $PSScriptRoot "..\\..\\models\\BitNet-b1.58-2B-4T\\ggml-model-i2_s.gguf"),
    (Join-Path $PSScriptRoot "..\\..\\models\\ggml-model-i2_s.gguf"),
    (Join-Path $PSScriptRoot "models\\ggml-model-i2_s.gguf")
)

$modelPath = $null
foreach ($cand in $modelCandidates) {
    if (Test-Path $cand) {
        $modelPath = (Resolve-Path $cand).Path
        break
    }
}

if (-not (Test-Path $exePath)) {
    Write-Host "[ERROR] Binary not found at $exePath" -ForegroundColor Red
    exit 1
}

if (-not $modelPath) {
    $targetDir = Join-Path $PSScriptRoot "..\\..\\models\\BitNet-b1.58-2B-4T"
    if (-not (Test-Path $targetDir)) { New-Item -ItemType Directory -Path $targetDir -Force | Out-Null }
    $modelPath = Join-Path $targetDir "ggml-model-i2_s.gguf"
    $url = "https://huggingface.co/microsoft/BitNet-b1.58-2B-4T-gguf/resolve/main/ggml-model-i2_s.gguf"
    Write-Host "[INFO] Downloading BitNet weights (~1.2 GB) to $modelPath..." -ForegroundColor Yellow
    Start-BitsTransfer -Source $url -Destination $modelPath -DisplayName "BitNet Model Download"
    Write-Host "[OK] Download completed successfully!" -ForegroundColor Green
}

Write-Host "Starting BitNet llama-server on http://127.0.0.1:$port (Threads: $threads) ..." -ForegroundColor Green
Write-Host "Model: $modelPath" -ForegroundColor Gray
Write-Host "OpenAI API endpoint: http://127.0.0.1:$port/v1" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop." -ForegroundColor Gray
Write-Host "============================================================" -ForegroundColor Cyan

& $exePath `
    -m $modelPath `
    --host 127.0.0.1 `
    --port $port `
    -t $threads `
    --repeat-penalty 1.15 `
    --repeat-last-n 64 `
    --top-p 0.9 `
    --min-p 0.05 `
    --temp 0.7 `
    -c 4096
"""
(sidecar_dir / "start-portable.ps1").write_text(start_portable_ps1, encoding="utf-8")

# 4. start-portable.bat
start_portable_bat = """@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-portable.ps1"
pause
"""
(sidecar_dir / "start-portable.bat").write_text(start_portable_bat, encoding="utf-8")

# 5. scripts/start-docker.ps1
start_docker_ps1 = """$ErrorActionPreference = "Stop"
Write-Host "Starting Alamia BitNet Runtime Docker sidecar..." -ForegroundColor Cyan
docker compose -f "$PSScriptRoot\\..\\docker-compose.yml" up -d
Write-Host "[OK] BitNet sidecar started on port 8080." -ForegroundColor Green
"""
(sidecar_dir / "scripts" / "start-docker.ps1").write_text(start_docker_ps1, encoding="utf-8")

# 6. scripts/stop-docker.ps1
stop_docker_ps1 = """$ErrorActionPreference = "Stop"
Write-Host "Stopping Alamia BitNet Runtime Docker sidecar..." -ForegroundColor Yellow
docker compose -f "$PSScriptRoot\\..\\docker-compose.yml" down
Write-Host "[OK] BitNet sidecar stopped." -ForegroundColor Green
"""
(sidecar_dir / "scripts" / "stop-docker.ps1").write_text(stop_docker_ps1, encoding="utf-8")

# 7. scripts/test.ps1
test_ps1 = """$ErrorActionPreference = "Stop"
Write-Host "Testing BitNet Inference Provider at http://localhost:8080/v1/chat/completions..." -ForegroundColor Cyan

$body = @{
    model = "bitnet_b1_58_2b"
    messages = @(
        @{
            role = "user"
            content = "Explain the advantages of 1-bit ternary quantization in one sentence."
        }
    )
    temperature = 0.2
    max_tokens = 64
} | ConvertTo-Json -Depth 5

$t0 = Get-Date
try {
    $resp = Invoke-RestMethod -Uri "http://localhost:8080/v1/chat/completions" -Method Post -Body $body -ContentType "application/json"
    $dur = (Get-Date) - $t0
    Write-Host "[OK] Response received in $($dur.TotalMilliseconds)ms:" -ForegroundColor Green
    Write-Host $resp.choices[0].message.content -ForegroundColor White
} catch {
    Write-Host "[ERROR] Could not connect to BitNet server at http://localhost:8080: $_" -ForegroundColor Red
}
"""
(sidecar_dir / "scripts" / "test.ps1").write_text(test_ps1, encoding="utf-8")

# 8. README.md
readme_content = """# Alamia BitNet Runtime Service (.sidecar/alamia-bitnet-runtime)

This directory houses the dedicated **BitNet Execution Provider** for the Alamia Local AI Runtime, wrapping Microsoft's optimized `bitnet.cpp` runtime.

---

## Architectural Role

Per the Alamia Execution Fabric architecture, BitNet is an isolated, first-class execution provider. The core runtime interacts with it strictly via standard OpenAI-compatible HTTP endpoints:
- `POST /v1/chat/completions`
- `GET /health` or `GET /v1/models`

---

## Running Modes

### Mode 1: Native Windows Portable (Zero Docker)
Ideal for local Windows developers and low-end laptops:
```powershell
.\\start-portable.ps1
# or double click start-portable.bat
```
This runs `bin\\llama-server.exe` natively on `http://127.0.0.1:8080` against `../../models/BitNet-b1.58-2B-4T/ggml-model-i2_s.gguf`.

### Mode 2: Docker Container Sidecar
Ideal for containerized deployments:
```powershell
.\\scripts\\start-docker.ps1
```
Or via docker compose:
```bash
docker compose up -d
```

### Mode 3: Managed Remote VPS
Configured via `BITNET_SERVER_URL=https://ai.alamiaconnect.com/v1` in the main `.env`.
"""
(sidecar_dir / "README.md").write_text(readme_content, encoding="utf-8")

print("Successfully populated .sidecar/alamia-bitnet-runtime!")

