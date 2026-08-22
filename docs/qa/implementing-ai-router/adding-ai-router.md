Correct. Then we should **not architect the AI Employee around the Router yet**. The Router needs to become a foundational runtime capability first.

| Order  | Epic                        | Purpose                                                                        | Dependency |
| ------ | --------------------------- | ------------------------------------------------------------------------------ | ---------- |
| **E0** | Current Runtime Freeze      | Preserve the proven vertical/plugin architecture                               | ✅ Done     |
| **E1** | **AI Router Foundation**    | Route tasks across Local Model Garden → Local GPU → Frontier/Cloud             | **Now**    |
| **E2** | Model Capability Registry   | Describe models by capabilities, cost, latency, context, hardware requirements | E1         |
| **E3** | Routing Policy Engine       | Select model based on task type, constraints, availability, quality            | E1–E2      |
| **E4** | Execution/Fallback Layer    | Failover, retries, timeout, provider health, graceful degradation              | E1         |
| **E5** | Router Observability        | Decisions, latency, token/cost metrics, model outcomes                         | E1         |
| **E6** | AI Employee Upgrade         | Make `ai_employee` consume Router instead of directly choosing models          | E1–E5      |
| **E7** | Employee Intelligence Layer | Goals, memory, planning, skills, approvals, autonomy                           | E6         |
| **E8** | Productization              | Package employees + runtime + connectors as deployable products                | E7         |

### AI Router MVP DAG

```text
E1.0 Router PRD / contracts
        │
        ├── E1.1 Model Provider abstraction
        │       ├── Local Model Garden
        │       ├── Local GPU
        │       └── Cloud/Frontier
        │
        ├── E1.2 Model Capability Registry
        │
        ├── E1.3 Task Classification
        │
        ├── E1.4 Routing Policy Engine
        │
        ├── E1.5 Execution Adapter
        │
        ├── E1.6 Fallback / Retry / Timeout
        │
        ├── E1.7 Observability / Decision Trace
        │
        └── E1.8 Integration Tests
                    │
                    ▼
             ROUTER MVP PROOF
                    │
                    ▼
             AI Employee Integration
```

### Critical design decision

The Router should **not** be a glorified `if task == X → model Y`.

Its contract should eventually look conceptually like:

```text
Task
 ├─ type: extraction | embedding | rag | reasoning | coding | ...
 ├─ complexity
 ├─ quality_requirement
 ├─ latency_requirement
 ├─ privacy_requirement
 ├─ context_size
 ├─ budget
 └─ availability_constraints

                ↓

             AI ROUTER

                ↓

Candidate Models
 → capability matching
 → constraint filtering
 → scoring
 → health check
 → primary selection
 → fallback chain

                ↓

           Model Execution
                ↓
        Result + Trace
```

**Most important:** make the Router a **runtime service/primitive**, not an `ai_employee` feature.

Then every future vertical—AI Employee, RAG, document processing, QA agents, research agents, etc.—gets intelligent model selection automatically.

Given that your runtime architecture is already frozen for productization, I'd make **AI Router Sprint the next formal development sprint**, with a proper PRD → architecture contracts → DAG → atomic dev-agent tasks → acceptance tests → proof gates.
