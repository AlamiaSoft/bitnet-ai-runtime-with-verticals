Correct. Those are **missing product/platform layers**, and should be added before treating the Model Garden as complete.

### Revised DAG

```text
MODEL GARDEN
│
├── MG1 Model Catalog
│
├── MG2 Model Manifests
│
├── MG3 Model Acquisition
│   ├── download
│   ├── HuggingFace/source adapters
│   ├── version/checksum verification
│   ├── resume/retry
│   ├── storage management
│   └── license acceptance
│
├── MG4 Model Lifecycle
│   ├── installed
│   ├── available
│   ├── loading
│   ├── loaded
│   ├── update
│   └── remove
│
├── MG5 Runtime Integration
│   └── installed model → execution backend
│
├── MG6 Hardware Discovery
│   └── CPU/RAM/GPU → compatible models
│
└── MG7 Model Validation
    └── integrity + smoke test + capability verification


AI ROUTER
│
├── AR1 Capability Registry
├── AR2 Policy Engine
├── AR3 Candidate Selection
├── AR4 Execution
├── AR5 Fallback
└── AR6 Trace/Telemetry


MODEL GARDEN UX
│
├── UX1 Garden Dashboard
│   ├── Browse/search models
│   ├── capability filters
│   ├── hardware compatibility
│   └── model details
│
├── UX2 Installation
│   ├── Install
│   ├── Download progress
│   ├── Cancel/resume
│   └── Verify
│
├── UX3 Installed Models
│   ├── status
│   ├── storage
│   ├── default model
│   ├── update
│   └── uninstall
│
├── UX4 Router Configuration
│   ├── routing policies
│   ├── priorities
│   ├── privacy
│   ├── budget
│   └── fallback
│
└── UX5 Observability
    ├── routing decisions
    ├── model usage
    ├── latency
    └── token/cost metrics
```

### Revised Epic sequence

| Epic    | Deliverable                            |
| ------- | -------------------------------------- |
| **MG1** | Model Garden + manifests               |
| **MG2** | **Model Download/Acquisition Manager** |
| **MG3** | Model lifecycle + local storage        |
| **MG4** | Hardware compatibility/discovery       |
| **MG5** | Backend execution integration          |
| **UX1** | Garden UI                              |
| **UX2** | Installation/management UI             |
| **UX3** | Router configuration UI                |
| **UX4** | Observability UI                       |
| **AE1** | AI Employee upgrade                    |

**Critical direction:** don't let the dev agent treat "Model Garden" as a static Python catalog. It needs to become a **real model lifecycle subsystem**: *discover → download → verify → install → load → use → update → remove*.

And the UI should consume the same APIs/services rather than directly manipulating the Garden internals.
