# Architecture Alignment Report: The Unified Alamia Runtime Engine

**Date:** 2026-08-25  
**Scope:** Architectural reconciliation of all runtime subsystems into a single coherent execution brain.  
**Constraint:** Zero code edits until architectural reconciliation and lifecycle freeze are approved.

---

## 1. Executive Summary & Problem Statement

As the system has evolved, multiple specialized subsystems were engineered to solve critical operational requirements:
- `ModelGarden` for cataloging and streaming models to disk.
- `ModelCapabilityRegistry` & `AIRouter` for task-based model selection.
- `ExecutionRegistry` & backend drivers for dispatching inference to diverse runtimes.
- `MemorySubsystem` for SQLite conversation history and vector embeddings.
- `SecurityPolicyEngine` & `ToolSandbox` for evaluated tool execution.
- `SelfLearningAgent` for operator corrections and autonomous evolutionary optimization.
- `Verticals` for modular business domain applications.

However, to prevent this platform from becoming a collection of loosely coupled, fragmented components, this report establishes:
1. **The Reconciled Subsystem Map**: Explicit ownership, single source of truth, and strict boundaries for every subsystem.
2. **The Unified Execution Fabric**: Clear delineation between in-process local execution, sidecar network execution, and cloud escalation.
3. **The Canonical Request Lifecycle**: A deterministic, end-to-end flow from initial user prompt to evolutionary learning.

---

## 2. Subsystem Reconciliation Matrix

| Subsystem | Primary Responsibility | Single Source of Truth | What It Owns | What It Must NOT Do |
| :--- | :--- | :--- | :--- | :--- |
| **Model Garden & Lifecycle** (`model_garden`) | Model metadata catalog, on-disk file management, and HTTP streaming acquisition. | Catalog Manifests (`ModelManifest`) & Disk Directory (`/app/models/`). | GGUF/Safetensors files on disk, download state machines, SHA-256 verification, hardware compatibility profiling. | It does **not** evaluate task routing, execute prompts, or manage active process memory allocations. |
| **Model Capability Registry** (`router.registry`) | Dynamic index of available models mapped to capability scores, task ratings, and latency/cost profiles. | `ModelCapabilityRegistry` synchronized with live `ModelGarden` status. | Task-to-model benchmark matrix (quality score, extraction rating, reasoning rating, cost per 1k tokens). | It does **not** manage physical model files or directly invoke backend HTTP/C++ drivers. |
| **AI Router & Policy Engine** (`router`) | Translates task requirements into optimal primary and fallback execution decisions. | `RoutingPolicyEngine` scoring algorithm. | Mathematical candidate scoring, privacy boundaries (air-gapped vs local network vs cloud), fallback chain determination. | It does **not** execute models directly; it outputs a `RoutingDecision` for the `ExecutionRegistry`. |
| **Execution Registry & Inference Fabric** (`execution`) | Manages backend drivers (`llama.cpp`, `bitnet-server`, `TEI`), active RAM allocations, and execution dispatch. | `ExecutionRegistry` & `LoadedModelInstance` state. | Loading/unloading models into host RAM, backend health probing, in-process vs sidecar dispatch, prompt tokenization/generation. | It does **not** choose which model is best for a task; it executes whichever model manifest it is instructed to run. |
| **Inference Engines** (`inference`) | Low-level C++/Python/HTTP driver adapters. | Individual backend protocols (C++ bindings, OpenAI-compatible REST API). | In-process `llama-cpp-python` invocations, `bitnet-cli` subprocesses, sidecar HTTP POST requests. | They do **not** know about routing policies, vertical workflows, or user session state. |
| **Memory Subsystem** (`memory`) | Context persistence and semantic knowledge retrieval. | SQLite (`memory.db`) & vector index tables. | Episodic multi-turn dialogue, semantic document embeddings, nearest-neighbor vector search, employee state persistence. | It does **not** decide routing or execute tools. |
| **Tool Execution & Security Policy** (`tools`, `policy`) | Deterministic execution of external environment actions (shell, filesystem, browser). | `SecurityPolicyEngine` ruleset (`ALLOW`, `DENY`, `ASK`). | Tool sandboxing, argument validation, path traversal verification, human-in-the-loop approval gates. | It does **not** generate text or modify model weights directly. |
| **AI Employees & Verticals** (`agent`, `verticals`) | Domain-specific autonomous agents with business workflows. | Vertical Plugin Manifests (`bitnet.plugins`) & Persistent Personas. | Multi-step ReAct planning loops, domain KPI tracking, vertical-specific prompt templates and tool sets. | They do **not** bypass the AI Router or interact directly with raw hardware backends. |
| **Self-Learning & Evolution Engine** (`agent.self_learning`) | Continuous runtime optimization through operator corrections and benchmark sandboxes. | Learned Rules Table & Experience Log in SQLite. | Experience collection, outcome evaluation, rule induction, candidate strategy benchmarking, promotion gating. | It does **not** alter base GGUF model weights on disk; it refines routing heuristics, system prompts, and memory priors. |

---

## 3. Execution Fabric Strategy: Local vs. Sidecar vs. Cloud

The Alamia Runtime enforces a strict 3-tier execution hierarchy:

```text
                                 [ExecutionRegistry]
                                          │
        ┌─────────────────────────────────┼─────────────────────────────────┐
        ▼                                 ▼                                 ▼
   [Tier 1: Local In-Process]    [Tier 2: Dedicated Sidecar]     [Tier 3: Cloud Escalation]
   • Engine: llama-cpp-python    • Engine: bitnet-server         • Engine: OpenAI / Frontier
   • Target: /app/models/*.gguf  • Target: ai.alamiaconnect.com  • Target: api.openai.com
   • Scope: Qwen, Phi, Gemma,    • Scope: BitNet b1.58 2B-4T     • Scope: Complex reasoning
     BGE Embeddings, Reranker      (Ternary LUT / GEMM Kernels)    escalations (budget permitted)
   • Privacy: 100% Air-Gapped    • Privacy: Local LAN / Sidecar  • Privacy: External Net Allowed
```

### Key Execution Invariants:
1. **BitNet 1.58-Bit Models**:
   - Primary: Sidecar container (`ai.alamiaconnect.com` or local `bitnet-server` container on port 8080) hosting Microsoft's specialized C++ ternary kernel.
   - Secondary (Future): Direct in-container `bitnet-cli` execution if the binary is compiled into the Docker image.
2. **Standard GGUF Models (Qwen, Phi, Gemma, Llama)**:
   - Primary: In-process local execution via `llama-cpp-python` consuming `.gguf` files directly from `/app/models/`.
   - Secondary: Local `llama-server` instances if externalized.
3. **Embedding & Reranking Models (BGE Small, MiniLM, BGE Reranker)**:
   - Primary: In-process local vector computation via `llama-cpp-python` / `sentence-transformers` bindings.
   - Secondary: Hugging Face `TEI` backend for high-throughput batching.
4. **Cloud Frontier Models (GPT-4o, Claude)**:
   - Invoked strictly when task requirements permit `CLOUD_ALLOWED` privacy and zero-budget enforcement is not violated.

---

## 4. The Single Canonical Request Lifecycle

Every user prompt, AI Employee task, or vertical workflow executes through a single, deterministic 8-stage pipeline:

```text
┌─────────┐     ┌─────────┐     ┌───────────┐     ┌───────────┐
│ 1. USER │ ──> │ 2. AI   │ ──> │ 3. CAPAB. │ ──> │ 4. MODEL  │
│ REQUEST │     │ ROUTER  │     │ RESOLUT'N │     │ SELECTION │
└─────────┘     └─────────┘     └───────────┘     └───────────┘
                                                        │
┌─────────┐     ┌─────────┐     ┌───────────┐           │
│ 8. EVOL.│ <── │ 7. EXP. │ <── │ 6. VERIF. │ <── [5. EXECUTION]
│ ENGINE  │     │ RECORD  │     │ & GUARD   │     (Inference Fabric)
└─────────┘     └─────────┘     └───────────┘
```

### Stage 1: Request Ingestion & Intent Extraction
- **Input**: User prompt, task requirements (latency, privacy, quality threshold), and session metadata.
- **Action**: 
  - Retrieve conversational context from `EpisodicMemory`.
  - Perform semantic retrieval from `SemanticMemory` to gather relevant knowledge base chunks.
  - Apply active Learned Rules from the `SelfLearningAgent` matching the current intent context.

### Stage 2: AI Routing & Policy Evaluation
- **Input**: Synthesized task requirements, privacy policy, budget constraints.
- **Action**:
  - `RoutingPolicyEngine` inspects the live `ModelCapabilityRegistry`.
  - Computes candidate scores for all installed and loaded models.
  - Builds an optimal `RoutingDecision` containing:
    - Primary candidate model.
    - Ordered fallback chain.
    - Mathematical rationale.

### Stage 3: Execution Fabric Model Preparation
- **Input**: Target model manifest from the routing decision.
- **Action**:
  - `ExecutionRegistry` verifies if the target model is currently loaded in host RAM.
  - If not loaded, invokes `load_model(manifest)` to allocate memory and initialize the appropriate driver (`llama-cpp-python` for local GGUF, or `BitNetBackend` for the sidecar).

### Stage 4: Inference Execution & Tool Invocations
- **Input**: System prompt, context chunks, user prompt, available tools.
- **Action**:
  - The resolved inference engine generates tokens.
  - If the model emits structured tool calls (`{"tool": "run_shell", "args": {...}}`), control passes to the `SecurityPolicyEngine`.
  - The policy engine evaluates boundaries:
    - `ALLOW`: Executes sandboxed tool in workspace.
    - `DENY`: Intercepts and returns a security refusal.
    - `ASK`: Suspends execution and creates a pending approval item in the Employee dashboard.

### Stage 5: Output Verification & Quality Guardrails
- **Input**: Raw model completion and tool execution results.
- **Action**:
  - Validates output structure (JSON schema validation for structured extraction, math consistency check for arithmetic queries).
  - If output fails schema or hallucinates known invariants, the AI Router triggers the next candidate in the fallback chain.

### Stage 6: Response Delivery & Stream Synthesis
- **Input**: Verified completion response.
- **Action**:
  - Formats output payload with complete execution telemetry (executed model ID, actual serving endpoint/backend, exact latency in ms, token counts, estimated cost).
  - Emits real-time SSE stream or HTTP response to the client.

### Stage 7: Telemetry & Experience Recording
- **Input**: Full end-to-end execution trace (`RoutingTrace`).
- **Action**:
  - Appends trace to `telemetry_collector` for dashboard observability.
  - Commits episodic dialogue turn into SQLite database.
  - Passes execution record to the `ExperienceCollector` in the evolution engine.

### Stage 8: Learning, Rule Induction & Evolutionary Loop
- **Input**: Stored execution experiences and operator feedback (approvals, edits, corrections).
- **Action**:
  - `OutcomeEvaluator` grades task success against expected benchmarks.
  - `StrategyOptimizer` synthesizes new operational rules (e.g., prompt constraints, tool routing adjustments).
  - Promotes validated rules into active inference memory, permanently eliminating repeat errors.

---

## 5. Next Steps for Implementation (Post-Freeze)

Once this architecture alignment is frozen and accepted:
1. **Integrate In-Process `llama-cpp-python`**:
   - Add `llama-cpp-python` dependency to `pyproject.toml` and Docker build.
   - Connect `LlamaCppEngine` directly to `/app/models/` for seamless in-process CPU execution of `qwen2.5_1.5b_instruct.gguf`, `phi3.5_mini_3.8b.gguf`, `gemma2_2b_it.gguf`, and `bge_small_en_v1.5.gguf`.
2. **Standardize Metadata Reporting on UI**:
   - Ensure the UI chat bubbles and traces consistently show the exact serving tier (`local in-process GGUF`, `bitnet-sidecar (ai.alamiaconnect.com)`, or `mock test-harness`).
3. **Verify Full Pipeline End-to-End**:
   - Benchmark Qwen 2.5 on structured extraction, BitNet on general conversation, and BGE on vector search.
