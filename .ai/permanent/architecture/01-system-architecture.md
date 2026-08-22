# Alamia Local AI Runtime Architecture

## 1. Executive Summary
**Alamia Local AI Runtime** is a local-first AI runtime designed for running capable AI models on everyday hardware ? without requiring a GPU or cloud AI APIs.

The platform is structured around 5 foundational pillars:
1. **?? Alamia Model Garden**: Curated catalog of high-efficiency 1?4B SLMs, vector embeddings, and sequence rerankers.
2. **?? Alamia AI Router**: Capability-aware routing engine selecting optimal models based on task requirements, privacy, and budget.
3. **? Alamia Inference Fabric**: Pluggable inference layer orchestrating mature OSS engines (`llama.cpp`, Microsoft `bitnet-server`, Hugging Face `TEI`).
4. **?? Alamia AI Employees**: Autonomous digital workers with persistent identities, task queues, and human approval gates.
5. **?? Alamia AI Verticals**: Modular business applications discovered dynamically via plugin contracts.

```text
                    ALAMIA LOCAL AI RUNTIME (:8000)
                                   ?
         ?????????????????????????????????????????????????????
         ?                         ?                         ?
  Alamia Model Garden       Alamia AI Router        Alamia AI Verticals
  (Curated SLM Catalog)   (Capability Selector)   (AI Employees & Auto)
         ?                         ?                         ?
         ?????????????????????????????????????????????????????
                                   ?
                        Alamia Inference Fabric
                                   ?
              ???????????????????????????????????????????
              ?                    ?                    ?
       llama.cpp Engine     BitNet 1-bit Engine     TEI Engine
      (Primary Foundation:   (Specialized 1-bit     (High-Throughput
       SLMs, Embed, Rerank)   Ternary Kernel)        Batch Embeddings)
              ?                    ?                    ?
        Qwen, Phi, Gemma       BitNet 2B-4T         BGE Embeddings
```

---

## 2. Core Architectural Invariants
1. **Local-First, CPU-First, Cloud-Optional**: Primary operations run on commodity CPU and host RAM without requiring external cloud APIs. When needed, the AI Router can escalate to cloud frontier models.
2. **Decoupled Dual-Layer Separation**:
   - **Runtime Core (`bitnet_runtime`)**: Model Garden, AI Router, Inference Fabric, Memory, Security Policy, ReAct Loop, Server, Dashboard, and Plugin Registry.
   - **Vertical Layer (`verticals`)**: Modular business applications discovered dynamically via entry points (`bitnet.plugins`).
3. **Inference Fabric Abstraction**: The runtime never hardcodes inference to a single binary. `ExecutionRegistry` dynamically resolves backend drivers (`llama.cpp`, `bitnet-server`, `TEI`, `mock`) with explicit model load/unload lifecycle and zero silent fallbacks.
4. **Deterministic Security Guardrails**: All tool and system operations are evaluated by `SecurityPolicyEngine` enforcing `ALLOW`, `DENY`, and `ASK` boundaries.
5. **Full Observability & Telemetry**: Every execution records task requirements, decision traces, prompts, responses, latencies, tokens, and costs.

---

## 3. Subsystem Responsibilities

### 3.1 Alamia Model Garden & Lifecycle (`bitnet_runtime.model_garden`)
- `ModelGarden`: Catalog of machine-readable manifests (`ModelManifest`) for CPU-friendly 1?4B SLMs (BitNet b1.58, Qwen 2.5, Phi-3.5, Gemma 2), dedicated embeddings (BGE Small, MiniLM), and rerankers.
- `ModelLifecycleManager`: Real model downloader with chunked HTTP streaming, checksum verification, disk quotas (`./models/`), and state transitions (`AVAILABLE ? DOWNLOADING ? INSTALLED ? LOADED ? UNLOADED ? REMOVED`).
- `HardwareDiscoveryEngine`: Host CPU architecture, SIMD extensions (AVX2, AVX512, NEON), and physical RAM evaluation.

### 3.2 Alamia AI Router (`bitnet_runtime.router`)
- `AIRouter`: Evaluates task requirements and routes to optimal model tier with automatic failover chains.
- `ModelCapabilityRegistry`: Dynamic capability registry synced with Model Garden.
- `RoutingPolicyEngine`: Mathematical scoring based on benchmark ratings, privacy constraints, and token limits.
- `RoutingTrace`: Telemetry recording candidate scores, latencies, token usage, and cost estimates.

### 3.3 Alamia Inference Fabric (`bitnet_runtime.execution`)
- `ExecutionBackend`: Abstract interface for `load_model`, `unload_model`, `complete`, `embed`, and `rerank`.
- `ExecutionRegistry`: Central orchestrator resolving operational engines, tracking active RAM allocations, and enforcing zero silent fallbacks.
- `LlamaCppBackend`: Primary driver for `llama.cpp` / `llama-server` (generative SLMs, embeddings, and reranking).
- `BitNetBackend`: Native driver for Microsoft BitNet b1.58 ternary sidecar container.
- `TEIBackend`: Driver for Hugging Face Text Embeddings Inference.
- `MockExecutionBackend`: Deterministic driver for offline test suites.

### 3.4 Memory Subsystem (`bitnet_runtime.memory`)
- `EpisodicMemory`: Tracks multi-turn dialogue history, tool traces, and session state in SQLite.
- `SemanticMemory`: Document chunking, vector indexing, and nearest-neighbor semantic retrieval.
- `DatabaseManager`: Thread-safe SQLite connection pool supporting disk and in-memory databases.

### 3.5 Security & Tools (`bitnet_runtime.tools`, `bitnet_runtime.policy`)
- `SecurityPolicyEngine`: Evaluates commands, blocks dangerous patterns, and verifies workspace directory boundaries.
- `RunShellTool`: Executes local terminal commands under policy guardrails.
- `FilesystemTool`: Safe file read/write/search confined to workspace directories.
- `BrowserTool`: Playwright-powered headless web automation.

### 3.6 Agent Subsystem (`bitnet_runtime.agent`)
- ReAct planning loop tailored for compact SLMs with markdown fenced JSON parsing.
- Argument-aware infinite loop detection.
- Context injection mitigation using `<retrieved_local_context>` XML boundaries.

### 3.7 Server, Web Dashboard & CLI (`bitnet_runtime.server`, `bitnet_runtime.cli`)
- FastAPI daemon exposing REST APIs (`/api/v1/garden`, `/api/v1/execution`, `/api/v1/router`, `/api/v1/agents`, `/api/v1/memory`, `/api/v1/webhooks`) and SSE streaming.
- Interactive Single-Page Web Dashboard (`/dashboard`) with Model Garden, Model Playground, Inference Fabric diagnostics, Hardware & Storage, AI Router Studio, and Telemetry Logs.
- Typer CLI providing commands (`serve`, `info`, `run`, `ingest`, `search`, `vertical`).
