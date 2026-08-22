# Alamia Local AI & BitNet VPS Deployment Guide

This directory contains standalone, Portainer-compatible Docker Compose stacks for deploying on a VPS (such as a Hetzner CX43 AMD server).

---

## ??? Architecture: Two Independent Stacks

```text
       Cloudflare Zero Trust / Cloudflare Tunnel
                           ?
       ?????????????????????????????????????????
       ? (HTTPS / SSO)                         ? (Bearer Auth)
 console.alamiaconnect.com               ai.alamiaconnect.com
       ?                                       ?
  127.0.0.1:8000                          127.0.0.1:11434
       ?                                       ?
 ?????????????????????????????????       ?????????????????????????????????
 ? STACK 2: Alamia Local AI      ????????? STACK 1: BitNet Sidecar       ?
 ? (Console, Router, Memory, SLMs)? HTTPS ? (Microsoft 1-Bit 2B-4T Kernel) ?
 ?????????????????????????????????       ?????????????????????????????????
```

---

## 1. Stack 1: Microsoft BitNet 1-Bit Sidecar (`docker-compose.yml`)

The dedicated ternary kernel container that runs the baked 1.2 GB BitNet b1.58 2B-4T model.

### Deployment in Portainer:
1. Create a new stack: **`bitnet-sidecar`**.
2. Point Git repository to `deploy/docker-compose.yml`.
3. Set environment variables:
   - `BITNET_API_KEY`: `<your_secure_random_token>`
4. Deploy. The container binds to `127.0.0.1:11434`.
5. In Cloudflare Tunnel, route **`ai.alamiaconnect.com`** $	o$ `http://localhost:11434`.

---

## 2. Stack 2: Alamia Local AI Runtime & Console (`docker-compose.alamia.yml`)

The primary platform runtime containing the Model Garden, AI Router, Inference Fabric (`llama.cpp` + `BitNet`), AI Employees, Memory OS, and interactive Web Console.

### Deployment in Portainer:
1. Create a new stack: **`alamia-local-ai`**.
2. Point Git repository to `deploy/docker-compose.alamia.yml`.
3. Set environment variables:
   - `BITNET_SERVER_URL`: `https://ai.alamiaconnect.com/v1` (or `http://127.0.0.1:11434/v1`)
   - `BITNET_API_KEY`: `<your_secure_random_token>` (matches Stack 1 token)
   - `ALAMIA_RUNTIME_NAME`: `Alamia Local AI Runtime`
4. Deploy. The container binds to `127.0.0.1:8000`.
5. In Cloudflare Tunnel, route **`console.alamiaconnect.com`** $	o$ `http://localhost:8000`.

---

## ?? Security Hardening & Constraints

- **Localhost Binding Only**: Neither stack binds to `0.0.0.0` on the host, preventing raw public port exposure.
- **Bearer Token Authentication**: When Alamia Local AI makes requests to `ai.alamiaconnect.com`, it automatically sends `Authorization: Bearer <BITNET_API_KEY>`.
- **Cloudflare WAF / Rate Limiting**: Configure a Cloudflare rate limit rule on `ai.alamiaconnect.com` (e.g. 60 req/min).
- **Persistent Storage**:
  - `alamia_local_ai_models`: Persists downloaded `.gguf` weights across updates.
  - `alamia_local_ai_data`: Persists SQLite database and vector memory indexes.
