# Repository Index & Concept Map

| Concept | Directory / Path | Description |
|---|---|---|
| **Alamia Model Garden** | `bitnet_runtime/model_garden/` | 1?4B SLM catalog, dedicated embeddings, rerankers, hardware discovery, acquisition manager |
| **Alamia AI Router** | `bitnet_runtime/router/` | Policy-driven model routing, capability registry, fallback chains, decision traces |
| **Alamia Inference Fabric** | `bitnet_runtime/execution/` | Execution contracts, `LlamaCppBackend`, `BitNetBackend`, `TEIBackend`, `ExecutionRegistry` |
| **Legacy Inference Engines** | `bitnet_runtime/inference/` | BitNet b1.58 HTTP, LLaMA.cpp, Local Endpoint adapters |
| **Memory Subsystem** | `bitnet_runtime/memory/` | SQLite store, Vector Index, Episodic & Semantic Memory, Document Indexer |
| **Security Policy Engine** | `bitnet_runtime/policy/` | `SecurityPolicyEngine` with `ALLOW`, `DENY`, `ASK` capability evaluation |
| **Plugin & Vertical Registry** | `bitnet_runtime/plugins/` | `VerticalRegistry`, `VerticalManifest`, `VerticalPluginContract` |
| **Tool Registry** | `bitnet_runtime/tools/` | Filesystem, Shell (policy-governed), Browser (Playwright), HTTP tools |
| **Agent Orchestration** | `bitnet_runtime/agent/` | ReAct Loop, Cron Scheduler, Guardrails, Prompts |
| **API Server & Dashboard** | `bitnet_runtime/server/` | FastAPI REST/SSE Server and Reactive Web Dashboard (`/dashboard`) |
| **Execution REST API** | `bitnet_runtime/server/routes/execution.py` | Engine health, RAM memory allocation, explicit load/unload routes |
| **CLI Commands** | `bitnet_runtime/cli/` | Typer CLI commands (`serve`, `info`, `run`, `ingest`, `search`, `vertical`) |
| **Configuration** | `bitnet_runtime/config.py`, `.env`, `.env.example` | Pydantic Settings and dotenv environment variable mappings |
| **Alamia AI Employee** | `verticals/ai_employee/` | SMB Lead Triage, CRM, Inbox Responder, Tasks |
| **Personal Memory OS** | `verticals/personal_memory/` | Local File Watcher, Semantic Document Indexer |
| **AI Computer Operator** | `verticals/ai_computer/` | Desktop OS & Project Operator |
| **AI WhatsApp Employee** | `verticals/whatsapp_employee/` | Order, Booking & Chat Assistant Bridge |
| **AI QA Box** | `verticals/qa_box/` | Playwright E2E Test Crawler & Regression Monitor |
