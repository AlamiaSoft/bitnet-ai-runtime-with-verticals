# Current Sprint: Alamia Local AI Runtime - Foundation, Inference Fabric & Live Deployment

## Sprint Goal
Build the unified local AI agent runtime powered by small, capable AI models on everyday hardware with intelligent routing, replaceable serving engines (llama.cpp, bitnet-server, TEI), persistent memory, security guardrails, enterprise AI employee personas, and real-time observability.

## Completed Milestones
- [x] Knowledge base initialization (.ai/ docs)
- [x] Core runtime engine (inference, memory, tools, agent, server, CLI)
- [x] Verticals package (AI Employee, Personal Memory OS, AI Computer, WhatsApp Employee, QA Box)
- [x] Integration with live bitnet-server container at localhost:8080 and remote VPS (ai.alamiaconnect.com)
- [x] **Review 1 Remediations**:
  - [x] Decoupled runtime from verticals via dynamic plugin discovery (`VerticalRegistry`, `VerticalManifest`)
  - [x] Implemented deterministic capability and security policy engine (`SecurityPolicyEngine` with `PolicyDecision.ALLOW/DENY/ASK`)
  - [x] Fixed SQLite `:memory:` connection persistence in `DatabaseManager`
  - [x] Hardened ReAct loop with markdown fenced block JSON extraction, isolated prompt context delimiters (`<retrieved_local_context>`), and argument-aware loop detection
  - [x] Converted all hardcoded variables to environment variable and `.env` file loading (`.env`, `.env.example`, `pydantic-settings`, and `load_dotenv`)
  - [x] Entry-points plugin discovery (`importlib.metadata`) and isolated runtime tests (`tests/test_isolated_runtime.py`)
  - [x] Adversarial security & interactive `PolicyDecision.ASK` decision boundary verification (`tests/test_adversarial_security.py`)
  - [x] Standalone wheel packaging (`dist/bitnet_ai_runtime-0.1.0-py3-none-any.whl`)
- [x] **AI Router Foundation (Epics E1-E5)**:
  - [x] Model capability registry supporting Local 1-Bit, Local Dense, and Cloud Frontier tiers (`ModelCapabilityRegistry`)
  - [x] Constraint-based policy engine with airgap privacy, token limits, zero-budget, and quality scoring (`RoutingPolicyEngine`)
  - [x] Automated execution and failover fallback chain (`AIRouter`)
  - [x] Structured decision tracing, token accounting, and cost estimation (`RoutingTrace`)
- [x] **Model Garden Subsystem & Granular Capability Ratings**:
  - [x] Curated catalog for CPU-friendly 1-4B SLMs (BitNet b1.58, Qwen 2.5, Phi-3.5 Mini, Gemma 2, LLaMA 3.2), dedicated embedding models (BGE Small, MiniLM, BitNet hash), and specialized rerankers (`ModelGarden`)
  - [x] Machine-readable manifests with hardware constraints and benchmarked task ratings
  - [x] Decoupled modality separation preventing embedding models from contaminating generative pipelines
- [x] **Model Garden Lifecycle, Hardware Engine & Interactive Web UI (Epics MG2-MG5, UX1-UX5)**:
  - [x] Stateful acquisition and lifecycle manager with chunked streaming downloads and SHA256 checksums (`ModelLifecycleManager`)
  - [x] Hardware discovery engine evaluating host CPU architecture, RAM, and vector extensions (`HardwareDiscoveryEngine`)
  - [x] REST and SSE live progress streaming endpoints in FastAPI server (`/api/v1/garden`, `/api/v1/router`)
  - [x] Responsive single-page web dashboard at `/dashboard`
- [x] **Model Execution & Inference Fabric (Epics ME0-ME10)**:
  - [x] Abstract `ExecutionBackend` contracts and `ExecutionRegistry`
  - [x] Real `llama.cpp` (`llama-server`) backend as primary foundation for SLMs, embeddings, and reranking
  - [x] Hugging Face `TEI` backend for high-throughput batch vector embeddings
  - [x] Microsoft `BitNet` sidecar driver for native 1-bit ternary execution
  - [x] Dynamic backend resolution, active RAM tracking, explicit model loading/unloading
  - [x] REST routes: `GET /api/v1/execution/backends`, `GET /api/v1/execution/memory`, `POST /api/v1/execution/models/{id}/load`, `POST /api/v1/execution/models/{id}/unload`
- [x] **AI Employee Vertical Platform & 8 Digital Personas**:
  - [x] 8 specialized roles with tailored KPIs, tool permissions, and system instructions (`Alex Morgan`, `Maya Lin`, `Liam Vance`, `Dr. Elena Rostova`, `David Kim`, `Marcus Vance`, `Sophia Patel`, `Elena Torres`)
  - [x] SQLite-backed episodic self-learning memory engine (`learned_rules`) injecting operator feedback and invariants into prompt context
  - [x] Human-in-the-loop approval gate workflow with risk assessment (`ApprovalManager`)
  - [x] Dynamic API endpoints: `/api/v1/agents/employees`, `/task`, `/learnings`, `/feedback`, `/approvals`
- [x] **Mock Elimination & End-to-End Live Runtime Activation**:
  - [x] Injected Bearer token authentication (`BITNET_API_KEY`) into `BitNetEngine` and `BitNetBackend`
  - [x] Unified model path resolution (`/models/BitNet-b1.58-2B-4T/ggml-model-i2_s.gguf`) across direct model chat and router pipelines
  - [x] Baked live default server URL (`https://ai.alamiaconnect.com/v1`) and API key fallback into `config.py` and `docker-compose.yml`
  - [x] Fixed Model Garden install SSE progress stream routes (`/events` and `/acquire-stream`)
  - [x] Verified 100% genuine live completions in Playground Chat, Router, AI Employees, and Garden Chat
  - [x] **Full Test Suite Passing**: **65 / 65 unit and integration tests passed (100%)**

## Future Roadmap (Documented in Backlog)
1. **Alamia Evolution Engine**: Controlled learning loop (`ExperienceCollector` -> `Evaluator` -> `StrategyOptimizer` -> `SandboxBenchmark` -> `PromotionGate`).
2. **Deterministic Arithmetic & Math Verifier**: Short-circuiting arithmetic calculations to Python execution tools to eliminate SLM numerical hallucinations.
3. **Empirical Model Probing Suite**: Standardized local probing suite for arithmetic, JSON adherence, constraint compliance, and latency envelope.
