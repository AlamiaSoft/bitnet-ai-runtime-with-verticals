# Alamia BitNet Runtime Service (.sidecar/alamia-bitnet-runtime)

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
.\start-portable.ps1
# or double click start-portable.bat
```
This runs `bin\llama-server.exe` natively on `http://127.0.0.1:8080` against `../../models/BitNet-b1.58-2B-4T/ggml-model-i2_s.gguf`.

### Mode 2: Docker Container Sidecar
Ideal for containerized deployments:
```powershell
.\scripts\start-docker.ps1
```
Or via docker compose:
```bash
docker compose up -d
```

### Mode 3: Managed Remote VPS
Configured via `BITNET_SERVER_URL=https://ai.alamiaconnect.com/v1` in the main `.env`.
