# Repository Index & Concept Map

| Concept | Directory / Path | Description |
|---|---|---|
| Model Garden & Lifecycle | `bitnet_runtime/model_garden/` | 1-4B SLMs, dedicated embeddings, rerankers, hardware compatibility, and acquisition manager |
| AI Router Subsystem | `bitnet_runtime/router/` | Policy-driven model routing, capability registry, fallback chains, decision traces |
| Inference Engine | `bitnet_runtime/inference/` | BitNet b1.58 HTTP / binary, LLaMA.cpp, Local Endpoint, Feature Hash Embeddings |
| Memory Subsystem | `bitnet_runtime/memory/` | SQLite store, Vector Index, Episodic & Semantic Memory, Document Indexer |
| Security Policy Engine | `bitnet_runtime/policy/` | `SecurityPolicyEngine` with `ALLOW`, `DENY`, `ASK` capability rules |
| Plugin & Vertical Registry | `bitnet_runtime/plugins/` | `VerticalRegistry`, `VerticalManifest`, `VerticalPluginContract` |
| Tool Registry | `bitnet_runtime/tools/` | Filesystem, Shell (policy-governed), Browser (Playwright), HTTP tools |
| Agent Orchestration | `bitnet_runtime/agent/` | ReAct Loop, Cron Scheduler, Guardrails, Prompts |
| API Server & Web Dashboard | `bitnet_runtime/server/` | FastAPI REST/SSE Server and Reactive Web Dashboard (`/dashboard`) |
| CLI Commands | `bitnet_runtime/cli/` | Typer CLI commands (`serve`, `info`, `run`, `ingest`, `search`, `vertical`) |
| Configuration | `bitnet_runtime/config.py`, `.env`, `.env.example` | Pydantic Settings and dotenv environment variable mappings |
| AI Employee Vertical | `verticals/ai_employee/` | SMB Lead Triage, CRM, Inbox Responder, Tasks |
| Personal Memory OS | `verticals/personal_memory/` | Local File Watcher, Semantic Document Indexer |
| AI Computer Vertical | `verticals/ai_computer/` | Desktop OS & Project Operator |
| WhatsApp Employee | `verticals/whatsapp_employee/` | Order, Booking & Chat Assistant Bridge |
| QA Box Vertical | `verticals/qa_box/` | Playwright E2E Test Crawler & Regression Monitor |
