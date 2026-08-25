Yes. I would make this the **next major productization phase**, but keep it strictly downstream of the frozen runtime architecture. The goal is not "add an API"; it is to turn Alamia Local AI Runtime into an **AI execution platform that applications and AI Employees consume through a stable API contract**.

## PRD — Alamia AI Runtime API & Production Execution Layer

### Product objective

Expose Alamia Local AI Runtime as a **local/private AI service** that production applications and AI Employees can consume without knowing which model, backend, hardware, or execution strategy is being used.

**Core contract:**

```text
Application / AI Employee
        ↓
   Alamia AI API
        ↓
      Router
        ↓
 Capability + Policy
        ↓
 Routing Decision
        ↓
 Verification / Fallback
        ↓
 Execution Fabric
        ↓
 BitNet / Qwen / Phi / Gemma / GPU / Cloud
```

The consuming application should never need to know:

* model filename
* GGUF format
* llama.cpp
* BitNet server
* GPU availability
* CPU capabilities
* model location
* sidecar URL
* fallback model

That is Alamia's responsibility.

---

# Architecture changes

### New logical layer

```text
┌──────────────────────────────────────────────┐
│              CONSUMER APPLICATIONS           │
│                                              │
│ Sales Employee │ Support │ WhatsApp │ SaaS   │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│              ALAMIA AI API                   │
│                                              │
│ Auth │ Validation │ Rate Limits │ Telemetry  │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│              AI ROUTER                      │
│                                              │
│ Policy │ Capability │ Hardware │ Learned     │
│ Rules  │ Registry   │ State    │ Rules       │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│           EXECUTION REGISTRY                 │
├───────────────┬───────────────┬──────────────┤
│ Local         │ Sidecar       │ Cloud        │
│ llama.cpp     │ BitNet        │ Frontier     │
└───────────────┴───────────────┴──────────────┘
```

---

# API design principle

Do **not** expose:

```text
POST /bitnet/generate
POST /qwen/generate
POST /llama/generate
```

Expose capabilities:

```text
POST /v1/chat
POST /v1/inference
POST /v1/extract
POST /v1/classify
POST /v1/embeddings
POST /v1/rerank
```

And eventually:

```text
POST /v1/agents/execute
```

The client expresses **what it needs**, not **how Alamia should do it**.

---

# DAG / Epics / Sprints

## EPIC 0 — Architecture & API Contract Freeze

**Goal:** Define the external contract before implementation.

### Tasks

* Define API versioning strategy
* Define request/response schemas
* Define task/capability taxonomy
* Define privacy policies
* Define latency/quality requirements
* Define streaming contract
* Define error model
* Define execution metadata schema
* Define authentication model
* Define tenant/application identity model
* Define backwards-compatibility rules

### Exit criteria

```text
API contract frozen
OpenAPI specification exists
No implementation-specific model concepts leak into API
```

---

# EPIC 1 — Alamia API Gateway

**Goal:** Make the runtime consumable over HTTP.

### Sprint 1

Implement:

```text
/v1/health
/v1/models
/v1/chat
/v1/inference
```

Features:

* request validation
* response serialization
* synchronous execution
* request IDs
* structured errors
* latency telemetry

### Sprint 2

Add:

```text
/v1/chat/stream
```

* SSE streaming
* cancellation
* timeout handling
* disconnect handling
* token telemetry

### Definition of Done

A completely separate application can connect to Alamia and perform inference without importing any Alamia Python internals.

---

# EPIC 2 — Authentication & Application Identity

This becomes important once the Sales Employee consumes the service.

### Tasks

Implement:

```text
Application
API Credential
Scopes
Permissions
```

Example:

```text
sales-agent-prod
    ↓
credential
    ↓
allowed:
    inference
    extraction
    embeddings
```

Later:

```text
tenant
 └── application
       └── credentials
```

Security requirements:

* hashed API keys
* credential rotation
* revocation
* scopes
* request audit trail
* no credentials in logs

---

# EPIC 3 — Capability-Based Inference

This is the **heart of the product**.

Instead of:

```json
{
  "model": "bitnet"
}
```

support:

```json
{
  "task": "extraction",
  "input": "...",
  "requirements": {
    "privacy": "local",
    "latency": "low"
  }
}
```

Router determines:

```text
extraction
    ↓
Capability Registry
    ↓
Qwen 1.5B
    ↓
llama.cpp
```

Another request:

```text
arithmetic
    ↓
Calculator
```

Another:

```text
conversation
    ↓
BitNet
```

---

# EPIC 4 — Verification & Intelligent Fallback

This should be implemented **before calling the API production-ready**.

### Pipeline

```text
Request
 ↓
Router
 ↓
Primary execution
 ↓
Verifier
 ↓
PASS ───────→ Response
 ↓
FAIL
 ↓
Fallback
 ↓
Verifier
 ↓
PASS
```

Implement validators for:

* JSON schema
* arithmetic
* tool results
* constraints
* safety
* timeout/failure
* model output validity

### Critical test

Your exact BitNet failure becomes an automated regression:

```text
Input:
2 + 200

Bad model:
402

Verifier:
FAIL

Fallback:
calculator

Final:
202
```

---

# EPIC 5 — Model Garden → Execution Integration

This is where the current `Models installed = 7` issue must be permanently resolved.

### Tasks

Separate:

```text
Artifact State
    AVAILABLE
    DOWNLOADING
    INSTALLED
    CORRUPTED
```

from:

```text
Execution State
    NOT_LOADED
    LOADING
    LOADED
    FAILED
```

Then ensure:

**Capability Registry only advertises executable models.**

Implement/test:

* BitNet
* BGE Small
* Qwen
* Phi
* Gemma
* Llama
* BGE Reranker

The architecture already defines Model Garden as the owner of physical model files and Execution Registry as the owner of active execution state. 

---

# EPIC 6 — Production Execution Providers

Standardize:

```text
ExecutionProvider
```

Implement:

### Provider 1

```text
LocalLlamaCppProvider
```

### Provider 2

```text
BitNetSidecarProvider
```

### Provider 3

```text
CloudProvider
```

Cloud provider must be optional.

The frozen architecture explicitly establishes these three execution providers. 

---

# EPIC 7 — AI Employee SDK

This is where the API becomes genuinely useful.

Provide a tiny client abstraction:

```python
alamia.chat(...)
alamia.extract(...)
alamia.classify(...)
alamia.embed(...)
alamia.execute(...)
```

A Sales Employee should be able to do:

```text
Sales Employee
      ↓
Alamia SDK
      ↓
Alamia API
```

without knowing anything about the underlying model.

Potential SDKs later:

```text
Python
PHP
JavaScript/TypeScript
```

Given your ecosystem, **Python + PHP + TypeScript** would eventually be the useful trio.

---

# EPIC 8 — Observability & Runtime Control Plane

Every request should produce a trace:

```text
request_id
application_id
task
routing_decision
model
provider
fallbacks
latency
tokens
verification
final_status
```

Example:

```text
REQ-92831

Task: extraction
Primary: Qwen 2.5 1.5B
Provider: llama.cpp/local
Latency: 812ms
Verification: PASS
Fallback: none
```

The UI should expose this.

This is particularly important because the Runtime is becoming an **inference control plane**, not merely a chat UI.

---

# EPIC 9 — Self-Learning / Evolution Integration

**Last, not first.**

Only after the API + routing + verification system is stable.

Pipeline:

```text
API request
 ↓
Routing
 ↓
Execution
 ↓
Verification
 ↓
Experience
 ↓
Evaluator
 ↓
Candidate Rule
 ↓
Regression Sandbox
 ↓
PASS?
 ├── NO → discard
 └── YES → promote
```

Never allow the learning subsystem to directly mutate routing policy.

Your frozen architecture already establishes exactly this regression-gated promotion invariant. 

---

# EPIC 10 — Production Hardening

Before calling the API production-ready:

* authentication tests
* authorization tests
* rate limits
* concurrency tests
* memory pressure
* model loading contention
* request cancellation
* provider failure
* sidecar unavailable
* cloud unavailable
* malformed model
* corrupted model
* oversized request
* prompt injection through tools
* audit logging
* graceful shutdown
* health/readiness probes

---

# Recommended sprint sequence

| Sprint  | Focus                       | Result                              |
| ------- | --------------------------- | ----------------------------------- |
| **S0**  | API contract                | OpenAPI frozen                      |
| **S1**  | API Gateway                 | External app can call Alamia        |
| **S2**  | Auth + application identity | Secure consumers                    |
| **S3**  | Capability routing          | API → Router → model/tool           |
| **S4**  | Verification + fallback     | Bad model output recovered          |
| **S5**  | Model Garden integration    | Real executable Model Garden        |
| **S6**  | Execution providers         | Local + BitNet + optional cloud     |
| **S7**  | SDK                         | AI Employees consume Alamia cleanly |
| **S8**  | Observability/control plane | Production telemetry                |
| **S9**  | Self-learning               | Regression-gated evolution          |
| **S10** | Hardening                   | Production readiness                |

## The key DAG

```text
S0 API Contract
      │
      ▼
S1 API Gateway
      │
      ├──────────────┐
      ▼              ▼
S2 Auth          S5 Model Garden
      │              │
      └──────┬───────┘
             ▼
       S3 AI Router
             │
             ▼
       S4 Verification
             │
             ▼
       S6 Execution Fabric
             │
             ▼
          S7 SDK
             │
             ▼
      AI Employees
             │
             ▼
      S8 Observability
             │
             ▼
      S9 Self-Learning
             │
             ▼
       S10 Hardening
```

### Most important product milestone

Don't aim for "API completed."

Aim for this demonstrable scenario:

```text
Sales AI Employee
       │
       │ POST /v1/inference
       ▼
Alamia API
       │
       ▼
AI Router
       │
       ├── determines extraction
       ├── selects Qwen
       ├── verifies output
       └── falls back if necessary
       │
       ▼
Structured result
       │
       ▼
Sales Employee continues
```

**The Sales Employee should be completely ignorant of whether Alamia used BitNet, Qwen, a calculator, a GPU model, or eventually a frontier model.**

That is the abstraction I'd build the entire product around.

And I would give the coding agent this PRD **as the implementation boundary**, while explicitly telling it: **do not alter the frozen core architecture; implementation must conform to the existing Architecture Alignment Report.**
