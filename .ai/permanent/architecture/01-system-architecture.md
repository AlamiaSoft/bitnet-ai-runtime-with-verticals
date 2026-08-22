# BitNet AI Runtime Architecture

## 1. Executive Summary
BitNet AI Runtime is a local, privacy-preserving, zero-cloud-cost agent execution framework designed to harness 1-bit and extreme-quantization LLMs (such as Microsoft BitNet b1.58, 2.4B BitNet, and quantized edge models). 

Instead of treating 1-bit LLMs as simple chat interfaces, the architecture leverages the unique economics of continuous local CPU inference to run autonomous background agents, continuous observation, persistent episodic/semantic memory, and vertical business solutions.

---

## 2. Core Architectural Invariants
1. **Local-First & Offline Capable**: Zero mandatory external cloud dependencies or API keys for primary operation. All vector embeddings, document parsing, state transitions, and inference run on commodity CPU/hardware.
2. **Decoupled Dual-Layer Separation**:
   - **Engine Layer (`bitnet_runtime`)**: Model management, inference drivers, AI Router, vector & SQLite memory, ReAct loop, tool sandbox, scheduler, local REST/SSE server, security policy engine, and dynamic plugin registry. Zero static compile-time imports of vertical applications.
   - **Vertical Layer (`verticals`)**: Domain-specific agents (AI Employee, Personal Memory OS, AI Computer, AI WhatsApp Employee, QA Box) implementing `VerticalPluginContract` and `VerticalManifest`. Discovered dynamically via `VerticalRegistry` and Python entry points (`bitnet.plugins`).
3. **Pluggable Inference Abstraction**: Uniform interface (`InferenceEngine`) supporting native BitNet runners (`bitnet.cpp` / `bitnet-server` container on `localhost:8080`), quantized GGUF (`llama.cpp`), and local mock/endpoint fallbacks (`LocalEndpointEngine`).
4. **Deterministic Security Policy Engine**: All OS/filesystem/shell/browser operations pass through `SecurityPolicyEngine` enforcing strict capability evaluation (`ALLOW`, `DENY`, `ASK`), critical execution pattern detection, subshell parsing, and workspace path confinement.
5. **Environment-Driven Configuration**: All parameters, model paths, ports, and provider selections are managed via `pydantic-settings` and `.env` environment variables.

---

## 3. Subsystem Responsibilities

### 3.1 Inference Subsystem (`bitnet_runtime.inference`)
- `InferenceEngine`: Abstract contract for prompt completion and streaming token generation.
- `BitNetEngine`: Direct HTTP driver for Microsoft BitNet server container (`localhost:8080/v1`) and local `bitnet.cpp` binaries.
- `LlamaCppEngine`: Fallback runner for GGUF models on CPU.
- `LocalEndpointEngine`: Adapter for local OpenAI-compatible endpoints (e.g., Ollama, LM Studio) during dev/testing.
- `EmbeddingEngine`: Compact / 1-bit embedding generator computing cosine similarities for retrieval.

### 3.2 AI Router Subsystem (`bitnet_runtime.router`)
- `AIRouter`: Foundational runtime primitive for intelligent, policy-driven model selection across Local 1-Bit, Local Dense, and Cloud tiers.
- `ModelCapabilityRegistry`: Multi-tier capability catalog tracking context windows, pricing, latency profiles, and health statuses.
- `RoutingPolicyEngine`: Mathematical scoring and hard constraint filter (airgap privacy, budget limits, context fit) generating primary selections and ordered fallback chains.
- `RoutingTrace`: Structured execution telemetry recording candidate scores, latencies, tokens, and cost estimates.

### 3.3 Memory Subsystem (`bitnet_runtime.memory`)
- `EpisodicMemory`: Tracks multi-turn interaction logs, agent observations, tool invocation history, and step transcripts in SQLite.
- `SemanticMemory`: Ingests unstructured files, chunks content, creates embeddings, and performs nearest-neighbor vector retrieval.
- `DatabaseManager`: Thread-safe SQLite manager maintaining persistent connections for in-memory and disk-backed configurations.
- `VectorStore`: Pure-Python / SQLite vector search store with cosine similarity.

### 3.4 Security & Tooling Subsystem (`bitnet_runtime.tools`, `bitnet_runtime.policy`)
- `SecurityPolicyEngine`: Evaluates commands, blocks dangerous patterns (`rm -rf /`, `del /s /q`, raw disk overrides, fork bombs), parses subcommands, and validates workspace directory boundaries.
- `RunShellTool`: Executes local terminal commands under policy engine constraints and timeouts.
- `FilesystemTool`: Safe file read/write/search confined to workspace directories.
- `BrowserTool`: Playwright-powered headless web automation.

### 3.5 Agent Subsystem (`bitnet_runtime.agent`)
- ReAct planning and self-correction loop tailored for compact/edge LLMs with markdown fenced JSON parsing.
- Argument-aware infinite loop detection (`detect_infinite_loop`).
- Context injection mitigation using `<retrieved_local_context>` XML boundary tags.
- `AgentScheduler`: Background cron and interval scheduler powered by APScheduler.

### 3.6 Plugin Subsystem (`bitnet_runtime.plugins`)
- `VerticalPluginContract`: Abstract base interface defining vertical lifecycle (`initialize()`, `get_cli_handlers()`).
- `VerticalManifest`: Structured metadata (`name`, `title`, `version`, `description`).
- `VerticalRegistry`: Dynamic auto-discovery, Python entry point discovery (`bitnet.plugins`), and instance manager.

### 3.7 Server & CLI Subsystem (`bitnet_runtime.server`, `bitnet_runtime.cli`)
- FastAPI local daemon exposing REST APIs (`/api/v1/agents`, `/api/v1/memory`, `/api/v1/webhooks`) and Server-Sent Events (SSE).
- Typer CLI providing commands (`serve`, `info`, `run`, `ingest`, `search`, `vertical`).
