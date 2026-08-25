# Current Sprint: Alamia Local AI Runtime - Foundation, Inference Fabric & Live Deployment

## Sprint Goal
Build the unified local AI agent runtime powered by small, capable AI models on everyday hardware with intelligent routing, replaceable serving engines (llama.cpp in-process and server, bitnet-server sidecar), persistent memory, security guardrails, enterprise AI employee personas, and real-time observability.

## Completed Milestones
- [x] Knowledge base initialization (.ai/ docs)
- [x] Core runtime engine (inference, memory, tools, agent, server, CLI)
- [x] Verticals package (AI Employee, Personal Memory OS, AI Computer, WhatsApp Employee, QA Box)
- [x] Integration with live bitnet-server container at localhost:8080 and remote VPS (ai.alamiaconnect.com)
- [x] **Review 1 Remediations**:
  - [x] Decoupled runtime from verticals via dynamic plugin discovery (VerticalRegistry, VerticalManifest)
  - [x] Implemented deterministic capability and security policy engine (SecurityPolicyEngine with PolicyDecision.ALLOW/DENY/ASK)
  - [x] Fixed SQLite :memory: connection persistence in DatabaseManager
  - [x] Hardened ReAct loop with markdown fenced block JSON extraction, isolated prompt context delimiters (<retrieved_local_context>), and argument-aware loop detection
  - [x] Converted all hardcoded variables to environment variable and .env file loading (.env, .env.example, pydantic-settings, and load_dotenv)
  - [x] Entry-points plugin discovery (importlib.metadata) and isolated runtime tests (	ests/test_isolated_runtime.py)
  - [x] Adversarial security & interactive PolicyDecision.ASK decision boundary verification (	ests/test_adversarial_security.py)
  - [x] Standalone wheel packaging (dist/bitnet_ai_runtime-0.1.0-py3-none-any.whl)
- [x] **AI Router Foundation (Epics E1-E5)**:
  - [x] Model capability registry supporting Local 1-Bit, Local Dense, and Cloud Frontier tiers (ModelCapabilityRegistry)
  - [x] Constraint-based policy engine with airgap privacy, token limits, zero-budget, and quality scoring (RoutingPolicyEngine)
  - [x] Automated execution and failover fallback chain (AIRouter)
  - [x] Structured decision tracing, token accounting, and cost estimation (RoutingTrace)
- [x] **Model Garden Subsystem & Granular Capability Ratings**:
  - [x] Curated catalog for CPU-friendly 1-4B SLMs (BitNet b1.58, Qwen 2.5, Phi-3.5 Mini, Gemma 2, LLaMA 3.2), dedicated embedding models (BGE Small, MiniLM, BitNet hash), and specialized rerankers (ModelGarden)
  - [x] Machine-readable manifests with hardware constraints and benchmarked task ratings
  - [x] Decoupled modality separation preventing embedding models from contaminating generative pipelines
- [x] **Model Garden Lifecycle, Hardware Engine & Interactive Web UI (Epics MG2-MG5, UX1-UX5)**:
  - [x] Stateful acquisition and lifecycle manager with chunked streaming downloads and SHA256 checksums (ModelLifecycleManager)
  - [x] Hardware discovery engine evaluating host CPU architecture, RAM, and vector extensions (HardwareDiscoveryEngine)
  - [x] REST and SSE live progress streaming endpoints in FastAPI server (/api/v1/garden, /api/v1/router)
  - [x] Responsive single-page web dashboard at /dashboard
- [x] **Dual-Mode Local Inference Fabric & Cloudflare Resilience**:
  - [x] Upgraded LlamaCppBackend to support **Mode 1 (In-Process CPU Execution)** via llama-cpp-python and **Mode 2 (Server HTTP Dispatch)**
  - [x] Parallelized BitNetBackend health probing with cached endpoints and browser headers clearing Cloudflare WAF bot challenges
  - [x] In-process chat templating (create_chat_completion) for Qwen, Phi, Gemma
  - [x] Transparent execution endpoint metadata on dashboard chat bubbles and telemetry traces
  - [x] Added cmake and pre-built CPU wheels to Dockerfile
- [x] **Canonical Architecture Alignment & Frozen Request Lifecycle**:
  - [x] Authored and froze docs/architecture-alignment-report.md
  - [x] Reconciled all 10 subsystems with single sources of truth
  - [x] Established 3-tier execution provider hierarchy and deterministic 8-stage request lifecycle
  - [x] Gated self-learning rules behind automated regression sandboxes
- [x] **API Capability Layer & Gateway (Sprints S0 & S1)**:
  - [x] Canonical Pydantic v2 capability schemas (InferenceRequest/Response, ChatRequest/Response, ExtractRequest/Response, ClassifyRequest/Response, EmbeddingRequest/Response, RerankRequest/Response, HealthResponse, ExecutionMetadata)
  - [x] Public capability router at `/v1` decoupling consuming applications (Sales Employee, WhatsApp Employee, microservices) from specific model names or GGUF files
  - [x] Automatic task-to-model capability resolution through AIRouter and ModelGarden
  - [x] High-performance SSE token streaming endpoint (`POST /v1/chat/stream`)
  - [x] Added `X-Request-ID` and `X-Response-Time-Ms` global request tracing middleware
  - [x] Authoritative 9-scenario API test suite (`tests/test_api_gateway.py`)
- [x] **Full Test Suite Passing**: **75 / 75 unit and integration tests passed (100%)**

## Current Focus & Next Steps
1. **Model Garden Physical Execution**: Validate in-process GGUF execution against physical models on disk.
2. **Client SDKs & Vertical Adapters (S2)**: Update Vertical AI Employee agents to consume the `/v1` capability contracts.
3. **Observability & Trace Ledger (S3)**: Connect the `/v1` execution traces to persistent SQLite observability ledger.
4. **Adaptive Caching (S4)**: Integrate deterministic prompt and semantic embedding cache on the `/v1` gateway.
