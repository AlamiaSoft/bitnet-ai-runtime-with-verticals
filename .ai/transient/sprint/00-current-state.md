# Current Sprint: Alamia Local AI Runtime ? Foundation & Inference Fabric

## Sprint Goal
Build the unified local AI agent runtime powered by small, capable AI models on everyday hardware with intelligent routing, replaceable serving engines (llama.cpp, bitnet-server, TEI), persistent memory, security guardrails, and enterprise vertical solutions.

## Completed Milestones
- [x] Knowledge base initialization (.ai/ docs)
- [x] Core runtime engine (inference, memory, tools, agent, server, CLI)
- [x] Verticals package (AI Employee, Personal Memory OS, AI Computer, WhatsApp Employee, QA Box)
- [x] Integration with live bitnet-server container at localhost:8080
- [x] Rigorous Architecture Audit (`docs/qa/review1.md`)
- [x] **Review 1 Remediations**:
  - [x] Decoupled runtime from verticals via dynamic plugin discovery (`VerticalRegistry`, `VerticalManifest`)
  - [x] Implemented deterministic capability and security policy engine (`SecurityPolicyEngine` with `PolicyDecision.ALLOW/DENY/ASK`)
  - [x] Fixed SQLite `:memory:` connection persistence in `DatabaseManager`
  - [x] Hardened ReAct loop with markdown fenced block JSON extraction, isolated prompt context delimiters (`<retrieved_local_context>`), and argument-aware loop detection
  - [x] Converted all hardcoded variables to environment variable and `.env` file loading (`.env`, `.env.example`, `pydantic-settings`, and `load_dotenv`)
  - [x] Entry-points plugin discovery (`importlib.metadata`) and isolated runtime tests (`tests/test_isolated_runtime.py`)
  - [x] Adversarial security & interactive `PolicyDecision.ASK` decision boundary verification (`tests/test_adversarial_security.py`)
  - [x] Standalone wheel packaging (`dist/bitnet_ai_runtime-0.1.0-py3-none-any.whl`)
- [x] **AI Router Foundation (Epics E1?E5)**:
  - [x] Model capability registry supporting Local 1-Bit, Local Dense, and Cloud Frontier tiers (`ModelCapabilityRegistry`)
  - [x] Constraint-based policy engine with airgap privacy, token limits, zero-budget, and quality scoring (`RoutingPolicyEngine`)
  - [x] Automated execution and failover fallback chain (`AIRouter`)
  - [x] Structured decision tracing, token accounting, and cost estimation (`RoutingTrace`)
- [x] **Model Garden Subsystem & Granular Capability Ratings**:
  - [x] Curated catalog for CPU-friendly 1?4B SLMs (BitNet b1.58, Qwen 2.5, Phi-3.5 Mini, Gemma 2, LLaMA 3.2), dedicated embedding models (BGE Small, MiniLM, BitNet hash), and specialized rerankers (`ModelGarden`)
  - [x] Machine-readable manifests with hardware constraints and benchmarked task ratings
  - [x] Decoupled modality separation preventing embedding models from contaminating generative pipelines
- [x] **Model Garden Lifecycle, Hardware Engine & Interactive Web UI (Epics MG2?MG5, UX1?UX5)**:
  - [x] Stateful acquisition and lifecycle manager with chunked streaming downloads and SHA256 checksums (`ModelLifecycleManager`)
  - [x] Hardware discovery engine evaluating host CPU architecture, RAM, and vector extensions (`HardwareDiscoveryEngine`)
  - [x] REST and SSE live progress streaming endpoints in FastAPI server (`/api/v1/garden`, `/api/v1/router`)
  - [x] Responsive single-page web dashboard at `/dashboard`
- [x] **Model Execution & Inference Fabric (Epics ME0?ME10)**:
  - [x] Abstract `ExecutionBackend` contracts and `ExecutionRegistry`
  - [x] Real `llama.cpp` (`llama-server`) backend as primary foundation for SLMs, embeddings, and reranking
  - [x] Hugging Face `TEI` backend for high-throughput batch vector embeddings
  - [x] Microsoft `BitNet` sidecar driver for native 1-bit ternary execution
  - [x] Deterministic `MockExecutionBackend` for test suites
  - [x] Dynamic backend resolution, active RAM tracking, explicit model loading/unloading
  - [x] Zero silent fallback policy
  - [x] REST routes: `GET /api/v1/execution/backends`, `GET /api/v1/execution/memory`, `POST /api/v1/execution/models/{id}/load`, `POST /api/v1/execution/models/{id}/unload`
- [x] **Platform Rebranding to Alamia Local AI Runtime**:
  - [x] Rebranded platform to **Alamia Local AI Runtime** (product family: **Alamia AI**)
  - [x] Formulated 5 core pillars: Alamia Model Garden, Alamia AI Router, Alamia Inference Fabric, Alamia AI Employees, Alamia AI Verticals
  - [x] Updated README.md, dashboard.html, app.py, config.py, and test suite
- [x] **System UI Upgrade: Interactive Alamia Local AI Console**:
  - [x] Adopted dark slate-moss console design from `docs/qa/System-ui/alamia-console.html`
  - [x] Connected all 8 views (Overview, Model Garden, Model Details, AI Router, AI Playground, AI Employees, Workflows, Activity & System)
  - [x] Integrated live SSE progress streaming for installation, RAM loading/unloading, live playground chat, vector embedding calculator, and real-time telemetry feed
- [x] **Hetzner CX43 AMD VPS Deployment & Live BitNet Connectivity**:
  - [x] Decoupled into two independent Portainer stacks: Microsoft BitNet Sidecar (`deploy/docker-compose.yml`) and Alamia Local AI Runtime (`deploy/docker-compose.alamia.yml`)
  - [x] Configured direct GitHub repository pulling and image building in Portainer
  - [x] Added Bearer token authentication (`BITNET_API_KEY`) to `BitNetBackend` and normalized base URL handling
  - [x] Verified live real-time completions against `https://ai.alamiaconnect.com/v1`
  - [x] **Test suite**: **61/61 tests passing** (100% pass rate)

## Next Sprint Milestone
- **Alamia AI Employee Vertical Review & Flagship Upgrade** (`docs/qa/ai-employee-vertical/review01.md`)

