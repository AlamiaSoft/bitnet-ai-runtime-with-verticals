Yes — **rename it now**. You have crossed the point where “BitNet Runtime” accurately describes the architecture.

### Brand direction

I would use:

**Alamia Local AI Runtime**

Short/internal:

**Alamia Local AI**

And position it as:

> **A local-first AI runtime for running capable AI models on everyday hardware — without requiring a GPU or cloud AI APIs.**

That is a much stronger product story than “BitNet runtime.”



### Your current architecture actually supports the rebrand

The stack is becoming:

```text
                    ALAMIA LOCAL AI RUNTIME
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
   Model Garden          AI Router           AI Verticals
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
                    Execution Fabric
                              │
             ┌────────────────┼────────────────┐
             │                │                │
          llama.cpp          TEI        BitNet engine
             │                │                │
        CPU SLMs          Embeddings       BitNet
        GGUF models       Rerankers        1-bit
```

The **BitNet model becomes one important model family**, not the identity of the platform.

### But I would change one thing in the agent's current plan

The proposed:

> `llama.cpp + TEI + bitnet-server`

is reasonable **as an implementation**, but don't expose those as the product architecture.

Your abstraction should be:

```text
Alamia Runtime
    ↓
Execution Fabric
    ↓
Capability-specific engines
```

And the engines remain replaceable.

Also, based on current llama.cpp capabilities, **don't assume TEI is mandatory for embeddings/reranking**. Current `llama-server` supports embeddings, reranking, CPU/GPU inference, and multi-model router mode itself. ([GitHub][1])

So I'd make the agent's architecture:

```text
Execution Fabric
│
├── llama.cpp backend        ← primary
│
├── BitNet backend           ← only where native BitNet support
│
└── TEI backend              ← specialized fallback/optimization
```

not:

```text
Generative → llama.cpp
Embedding → TEI
BitNet → bitnet-server
```

That latter mapping is unnecessarily rigid.

### And this becomes your moat

The interesting proposition isn't:

**“We run BitNet.”**

It's:

> **“We make a whole garden of small, specialized AI models usable on ordinary computers, automatically selecting the right model for each task.”**

Then your moat compounds:

**Model Garden → Local inference → Router → specialized capabilities → Verticals → persistent employee/agent workflows → telemetry/benchmarks**

That is substantially more defensible.

### Naming I would use

| Layer                  | Name                        |
| ---------------------- | --------------------------- |
| Company/product family | **Alamia AI**               |
| Runtime                | **Alamia Local AI Runtime** |
| Short name             | **Alamia Local AI**         |
| Model catalog          | **Alamia Model Garden**     |
| Router                 | **Alamia AI Router**        |
| Execution              | **Alamia Inference Fabric** |
| Business agents        | **Alamia AI Employees**     |
| Vertical ecosystem     | **Alamia AI Verticals**     |

And **BitNet stays in the stack as technology/model family**, with appropriate Microsoft attribution/licensing—not as your product brand.

One other important point: **don't prematurely market this as “no cloud ever.”** Your architecture is actually stronger:

> **Local-first, CPU-first, cloud-optional.**

That lets the Router escalate to GPU/cloud when the local garden isn't sufficient, without undermining the core proposition.

[1]: https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md?plain=1&utm_source=chatgpt.com "llama.cpp/tools/server/README.md at master · ggml-org/llama.cpp · GitHub"
