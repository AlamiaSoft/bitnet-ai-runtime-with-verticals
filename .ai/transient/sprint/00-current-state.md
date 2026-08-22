# Current Sprint: BitNet AI Runtime & Verticals Foundation

## Sprint Goal
Build the unified local AI agent runtime powered by 1-bit / edge inference with modular memory, tools, agent scheduler, REST/SSE server, CLI, and top 5 vertical business solutions.

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
  - [x] **Final Architectural Proof & Security Verification**:
    - [x] Entry-points plugin discovery (`importlib.metadata`) and isolated runtime tests (`tests/test_isolated_runtime.py`)
    - [x] Adversarial security & interactive `PolicyDecision.ASK` decision boundary verification (`tests/test_adversarial_security.py`)
    - [x] Standalone wheel packaging (`dist/bitnet_ai_runtime-0.1.0-py3-none-any.whl`)
    - [x] Expanded test suite to **40/40 tests passing** (100% pass rate)
  - [x] **AI Router Foundation (Epics E1–E5)**:
    - [x] Model capability registry supporting Local 1-Bit, Local Dense, and Cloud Frontier tiers (`ModelCapabilityRegistry`)
    - [x] Constraint-based policy engine with airgap privacy, token limits, zero-budget, and quality scoring (`RoutingPolicyEngine`)
    - [x] Automated execution and failover fallback chain (`AIRouter`)
    - [x] Structured decision tracing, token accounting, and cost estimation (`RoutingTrace`)
    - [x] Expanded test suite to **46/46 tests passing** (100% pass rate)
  - [x] **Model Garden Subsystem & Granular Capability Ratings**:
    - [x] Curated catalog for CPU-friendly 1–4B SLMs (BitNet b1.58, Qwen 2.5, Phi-3.5 Mini, Gemma 2, LLaMA 3.2), dedicated embedding models (BGE Small, MiniLM, BitNet hash), and specialized rerankers (`ModelGarden`)
    - [x] Machine-readable manifests with hardware constraints (`min_ram_mb`, `quantization`) and benchmarked task ratings (`task_ratings: Dict[TaskType, float]`)
    - [x] Decoupled modality separation preventing embedding models from contaminating generative pipelines
    - [x] Upgraded `ModelCapabilityRegistry` to dynamically sync from `ModelGarden`
    - [x] Expanded test suite to **50/50 tests passing** (100% pass rate)
  - [x] **Model Garden Lifecycle, Hardware Engine & Interactive Web UI (Epics MG2–MG5, UX1–UX5)**:
    - [x] Stateful acquisition and lifecycle manager with chunked downloads, SHA256 checksums, and on-disk storage tracking (`ModelLifecycleManager`)
    - [x] Hardware discovery engine evaluating host CPU architecture, RAM, and vector extensions (`HardwareDiscoveryEngine`)
    - [x] REST and SSE live progress streaming endpoints in FastAPI server (`/api/v1/garden`, `/api/v1/router`)
    - [x] Responsive single-page web dashboard at `/dashboard` (Model Garden catalog, download manager, hardware diagnostics, router studio, and live telemetry)
    - [x] Expanded test suite to **56/56 tests passing** (100% pass rate)
  - [x] **Full Platform Layer Complete** — Ready for AI Employee flagship vertical upgrade
