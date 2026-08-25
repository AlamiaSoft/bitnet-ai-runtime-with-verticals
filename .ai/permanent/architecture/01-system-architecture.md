# Architecture Alignment Report: The Unified Alamia Runtime Engine (FROZEN)

**Status:** Canonical & Frozen  
**Date:** 2026-08-25  
**Core Invariant:** Alamia must remain 100% fully functional on everyday CPU hardware with zero cloud connectivity. Cloud is strictly an optional escalation path.

---

## 1. Executive Summary & Principles

This document defines the canonical architecture for the **Alamia Local AI Runtime**. It establishes strict subsystem ownership, a unified 3-tier execution hierarchy, and a deterministic 8-stage request lifecycle.

```text
                               ALAMIA LOCAL AI
                                      │
                      ┌───────────────┴───────────────┐
                      ▼                               ▼
               LOCAL EXECUTION               OPTIONAL ESCALATION
             (100% Offline Core)             (Network / Cloud)
                      │                               │
         • Model Garden & Local GGUF        • BitNet Sidecar Container
         • In-Process llama.cpp Engine        (ai.alamiaconnect.com)
         • SQLite Episodic/Semantic Memory  • Cloud Frontier Models
         • Sandboxed Tools & Guardrails       (GPT-4o, Claude - Optional)
         • AI Router & AI Employees
```

---

## 2. Subsystem Ownership & Authority Boundaries

| Subsystem | Primary Responsibility | Single Source of Truth | What It Owns | What It Must NOT Do |
| :--- | :--- | :--- | :--- | :--- |
| **Model Garden** (`model_garden`) | Catalog metadata, on-disk model files, streaming downloads. | `ModelGarden` catalog manifests & disk directory (`/app/models/`). | GGUF/Safetensors on disk, download state machines, SHA-256 validation, hardware capability profiling. | It does **not** evaluate task routing, execute prompts, or manage active process memory allocations. |
| **Model Capability Registry** (`router.registry`) | Dynamic benchmark matrix of available models mapped to capability scores, task ratings, and cost/latency profiles. | `ModelCapabilityRegistry` synchronized with live `ModelGarden` status. | Task-to-model benchmark ratings (quality score, extraction rating, reasoning rating, cost per 1k tokens). | It does **not** manage physical model files or directly invoke backend HTTP/C++ drivers. |
| **AI Router & Policy Engine** (`router`) | Single authoritative decision-maker translating task requirements into optimal execution decisions. | `RoutingPolicyEngine` scoring algorithm. | Privacy boundaries (air-gapped vs network vs cloud), candidate scoring, complete `RoutingDecision` (primary model + fallback chain + tool selection). | It does **not** execute models directly; it instructs the `ExecutionRegistry` on what to run. |
| **Execution Registry & Inference Fabric** (`execution`) | Manages backend execution providers (`llama.cpp`, `bitnet-server`, `TEI`), active RAM allocations, and execution dispatch. | `ExecutionRegistry` & `LoadedModelInstance` state. | Loading/unloading models into host RAM, backend health probing, provider dispatch (`in-process`, `sidecar`, `cloud`), prompt tokenization/generation. | It does **not** make policy decisions or choose which model is best; it executes the `RoutingDecision`. |
| **Inference Engines** (`inference`) | Low-level C++/Python/HTTP driver adapters. | Individual backend protocols (C++ bindings, OpenAI-compatible REST API). | In-process `llama-cpp-python` invocations, `bitnet-cli` subprocesses, sidecar HTTP POST requests. | They do **not** know about routing policies, vertical workflows, or user session state. |
| **Memory Subsystem** (`memory`) | Context persistence and semantic knowledge retrieval. | SQLite (`memory.db`) & vector index tables. | Episodic multi-turn dialogue, semantic document embeddings, nearest-neighbor vector search, employee state persistence. | It does **not** decide routing or execute tools. |
| **Tool Execution & Security Policy** (`tools`, `policy`) | Deterministic execution of external environment actions (shell, filesystem, browser). | `SecurityPolicyEngine` ruleset (`ALLOW`, `DENY`, `ASK`). | Tool sandboxing, argument validation, path traversal verification, human-in-the-loop approval gates. | It does **not** generate text or modify model weights directly. |
| **Self-Learning & Evolution Engine** (`agent.self_learning`) | Continuous runtime optimization through operator corrections and benchmark sandboxes. | Learned Rules Table & Experience Log in SQLite. | Experience collection, outcome evaluation, candidate rule induction, regression benchmarking, promotion gating. | It does **not** modify raw user requests before routing; learned rules are candidate inputs evaluated by the Router only after validation. |
| **AI Employees & Verticals** (`agent`, `verticals`) | Domain-specific autonomous agents with business workflows. | Vertical Plugin Manifests (`bitnet.plugins`) & Persistent Personas. | Multi-step ReAct planning loops, domain KPI tracking, vertical-specific prompt templates and tool sets. | They do **not** bypass the AI Router or interact directly with raw hardware backends. |

---

## 3. The 3-Tier Execution Provider Architecture

The `ExecutionRegistry` treats backends as **execution providers**, while the `AIRouter` owns the privacy policy deciding which providers are permissible:

```text
                                 [ExecutionRegistry]
                                          │
        ┌─────────────────────────────────┼─────────────────────────────────┐
        ▼                                 ▼                                 ▼
   [Provider 1: In-Process]      [Provider 2: Sidecar]         [Provider 3: Cloud Escalation]
   • Driver: llama-cpp-python    • Driver: bitnet-server       • Driver: OpenAI / Anthropic
   • Scope: Qwen, Phi, Gemma,    • Scope: BitNet b1.58 2B-4T   • Scope: Complex reasoning
     BGE Embeddings, Reranker      (Ternary LUT / GEMM)          escalation (Optional)
   • Target: /app/models/*.gguf  • Target: Dedicated Container • Target: Cloud API
   • Privacy: 100% Air-Gapped    • Privacy: Local LAN/Sidecar  • Privacy: External Net (Opt-in)
```

---

## 4. The Single Canonical Request Lifecycle

Every user prompt, AI Employee task, or vertical workflow executes through a single, deterministic pipeline:

```text
                    [1. USER REQUEST]
                           │
                           ▼
               [2. INTENT & REQUIREMENTS]
             (Task Type, Privacy, Latency,
              Episodic & Semantic Context)
                           │
                           ▼
                    [3. AI ROUTER]
              ├── Static Policy
              ├── Capability Registry
              ├── Hardware & RAM State
              ├── Conversational Memory
              └── VALIDATED Learned Rules
                           │
                           ▼
                [4. ROUTING DECISION]
              (Primary Model + Fallback Chain
               + Tool Requirements + Rationale)
                           │
                           ▼
             [5. EXECUTION & TOOL RUNNER]
              (Execution Fabric In-Process/Sidecar
               + Security Policy Guardrail)
                           │
                           ▼
              [6. COMPREHENSIVE VERIFICATION]
              ├── Tool Result Validation
              ├── Structured JSON Schema Check
              ├── Arithmetic / Math Consistency
              ├── Factuality & Constraint Verification
              └── Safety & Policy Evaluation
                           │
                 ┌─────────┴─────────┐
             [PASSED]            [FAILED]
                 │                   │
                 ▼                   ▼
        [7. RESPONSE STREAM]   [TRIGGER NEXT
         & TELEMETRY LOG]       FALLBACK CANDIDATE]
                 │
                 ▼
       [8. EXPERIENCE RECORDING &
        REGRESSION-GATED LEARNING]
```

### Stage-by-Stage Specifications:

#### Stage 1: Request Ingestion
- Extracts raw prompt, explicit user preferences, and session context.

#### Stage 2: Intent & Context Synthesis
- Retrieves dialogue history from `EpisodicMemory`.
- Retrieves semantic knowledge base chunks from `SemanticMemory`.
- Synthesizes explicit requirements: `task_type` (extraction, arithmetic, reasoning, chat), `privacy` (airgapped, local network, cloud optional), and `latency`.

#### Stage 3: Authoritative AI Routing
- Evaluates models using `RoutingPolicyEngine`.
- **Inputs Evaluated**:
  1. Static system policy (e.g., air-gapped privacy enforcement).
  2. Live `ModelCapabilityRegistry` ratings.
  3. Real-time host RAM and backend health.
  4. Context tokens and budget constraints.
  5. **VALIDATED Learned Rules** (rules that have passed regression test sandboxes).

#### Stage 4: Routing Decision Output
- Emits an unambiguous `RoutingDecision` containing:
  - `primary_model`: Best candidate (e.g., Tool/Calculator for arithmetic, Qwen for extraction, BitNet for conversation).
  - `fallback_chain`: Ordered backup models.
  - `rationale`: Mathematical scoring justification.

#### Stage 5: Execution & Tool Sandboxing
- `ExecutionRegistry` loads model weights into RAM if not already loaded.
- Dispatches prompt to the resolved execution provider.
- If the model requests tool execution, `SecurityPolicyEngine` enforces `ALLOW`, `DENY`, or `ASK` (human approval gate).

#### Stage 6: Comprehensive Verification & Guardrails
- Evaluates output against multi-dimensional validators:
  1. **Tool Results Check**: Did the sandboxed tool succeed or return an error?
  2. **Schema Validation**: For extraction tasks, does output adhere strictly to the target JSON schema?
  3. **Arithmetic Consistency**: Does the computational result match exact math evaluators?
  4. **Factuality & Constraint Checks**: Are negative constraints respected?
  5. **Safety Guardrails**: Zero policy violations.
- **Failover Action**: If verification fails, the Router immediately advances to the next candidate in the `fallback_chain`.

#### Stage 7: Response Delivery & Observability
- Formats payload with serving metadata (`executed_model_id`, `endpoint`, `latency_ms`, `token_usage`, `estimated_cost_usd`).
- Delivers real-time SSE stream or REST response.
- Commits episodic turn to SQLite.

#### Stage 8: Experience Recording & Regression-Gated Evolution
- `ExperienceCollector` logs prompt, decision trace, execution output, and verification outcome.
- Operator corrections create *candidate rules*.
- **Promotion Invariant**: Candidate rules remain inactive until verified by automated regression sandboxes, preventing self-reinforcing failure loops.

---

## 5. Frozen Roadmap Sequence

With the architecture frozen, development follows this strict sequence:

1. **Local `llama.cpp` In-Process Execution**: *(Complete)*
2. **Model Garden GGUF Verification**: Verify Qwen 2.5, Phi-3.5, Gemma 2, and BGE on CPU.
3. **Capability Benchmarks Suite**: Build test harness covering extraction, arithmetic, reasoning, and search.
4. **Router Benchmark Validation**: Prove that arithmetic routes to tools/calculator, extraction routes to Qwen, and dialogue routes to BitNet.
5. **Comprehensive Verification & Fallback Loop**: Wire output validators directly into the router failover chain.
6. **Regression-Gated Self-Learning**: Enable candidate rule sandboxing and benchmark-gated promotion.
