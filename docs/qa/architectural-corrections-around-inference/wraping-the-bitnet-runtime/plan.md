 **I would change the BitNet execution architecture.** Given what you've already proven, I would stop treating `bitnet-cli` as the primary in-process execution path for Alamia.

Microsoft's current BitNet project itself is built around `bitnet.cpp`, with optimized CPU kernels, and its server launcher is effectively a server wrapper around the underlying llama.cpp-style server infrastructure. ([GitHub][1])

### My recommendation

Make BitNet a **first-class internal execution provider/service**, not a special case inside the Alamia Python process.

```text
                 ALAMIA LOCAL AI RUNTIME
                          │
                     AI ROUTER
                          │
                  RoutingDecision
                          │
                 EXECUTION REGISTRY
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
       LOCAL PROVIDERS          INTERNAL SERVICES
              │                       │
       llama.cpp               BitNet Service
       Qwen/Phi/Gemma          │
              │                │
              │          Microsoft's
              │          bitnet.cpp
              │          optimized runtime
              │                │
              └───────┬────────┘
                      ▼
                 Verification
```

### Why?

You've already conducted the most important experiment:

**Microsoft BitNet server works correctly.**

**Direct Alamia BitNet execution does not.**

That tells us something valuable: **the problem isn't BitNet inference itself; it's our integration boundary.**

And Microsoft continues to optimize BitNet specifically at the kernel/runtime level — including native I2_S GEMM/GEMV integration with the llama.cpp architecture. ([GitHub][2])

So I'd avoid duplicating Microsoft's execution machinery inside Alamia unless there is a compelling reason.

---

## But don't make it a "sidecar" conceptually

This distinction is important.

Today:

```text
Alamia → external BitNet sidecar
```

I'd evolve it to:

```text
Alamia
 └── Execution Provider
       └── BitNet Runtime Service
             └── bitnet.cpp
```

The service can physically be:

### Development

```text
Docker
├── alamia-runtime
└── bitnet-runtime
```

### Production single-machine

```text
Alamia Appliance
├── API
├── Router
├── Memory
├── Model Garden
├── llama.cpp
└── BitNet Runtime
```

### Enterprise/server

```text
Alamia Runtime
      │
      └── BitNet Provider
              │
              └── dedicated BitNet container/process
```

Same provider contract. Different deployment topology.

---

# The critical architectural rule

**The Router should never know that BitNet is a sidecar.**

It should only know:

```text
Provider:
    bitnet

Capabilities:
    conversation
    lightweight_generation
    local_cpu
    etc.

Health:
    available

Cost:
    local

Privacy:
    local
```

Then:

```text
ExecutionRegistry
       ↓
BitNetProvider
       ↓
HTTP / Unix socket / localhost
       ↓
BitNet Runtime
```

That means you can replace:

```text
bitnet.cpp server
```

with:

```text
future optimized BitNet runtime
```

without touching Router, Agents, API, Model Garden, or Memory.

---

## I would also remove this from the frozen architecture

Your current architecture says:

> BitNet primary = sidecar; secondary = future direct `bitnet-cli`.

I would revise that.

### New invariant

> **BitNet execution is provided by an isolated BitNet execution provider backed by Microsoft's `bitnet.cpp` runtime. Direct in-process BitNet execution is optional and non-authoritative.**

That is much safer.

The official project already provides a server launcher and builds the server as part of its environment setup. ([GitHub][3])

---

# There is an even bigger benefit

This makes your **Execution Fabric genuinely symmetrical**:

```text
                    ExecutionRegistry
                           │
       ┌───────────────────┼───────────────────┐
       ▼                   ▼                   ▼
 Local Llama          BitNet Provider      Cloud Provider
       │                   │                   │
   llama.cpp          BitNet Runtime       Frontier API
       │                   │
 Qwen/Phi/Gemma        BitNet
```

Then Alamia doesn't care whether inference happens:

* inside the Python process
* in another local process
* in a Docker container
* on another private machine
* through a cloud endpoint

**They're all execution providers.**

That's exactly what your architecture claims to be.

---

## One thing I would NOT do

Don't simply embed the existing Microsoft BitNet container as an opaque dependency and call it done.

Create an **Alamia-owned `BitNetProvider` contract**:

```text
BitNetProvider
├── health()
├── load_model()
├── unload_model()
├── generate()
├── stream()
├── metadata()
└── telemetry()
```

Behind it:

```text
BitNetProvider
       ↓
BitNet Runtime Adapter
       ↓
Microsoft bitnet.cpp server
```

Now Microsoft owns the inference implementation.

**Alamia owns the orchestration.**

That's the correct boundary.

### My final recommendation

**Yes: wrap/adapt Microsoft's BitNet server as an internal execution service and make it a first-class provider in the Execution Fabric.**

Don't spend engineering effort trying to make `bitnet-cli` behave like your other in-process engines unless later benchmarking proves there's a meaningful advantage.

You already have empirical evidence that the Microsoft server path works. **Use the working implementation as the foundation, isolate it behind your provider interface, and let Alamia's real differentiation remain Router + Verification + Model Garden + Memory + Agents + Evolution.**

[1]: https://github.com/microsoft/BitNet/blob/main/README.md?utm_source=chatgpt.com "BitNet/README.md at main · microsoft/BitNet · GitHub"
[2]: https://github.com/microsoft/BitNet/blob/main/src/README.md?utm_source=chatgpt.com "BitNet/src/README.md at main · microsoft/BitNet · GitHub"
[3]: https://github.com/microsoft/BitNet/blob/main/run_inference_server.py?utm_source=chatgpt.com "BitNet/run_inference_server.py at main · microsoft/BitNet · GitHub"
