Yes — the agent's diagnosis makes sense, and **this is a real architectural bug, not a cosmetic UI issue**.

The dashboard's `7` is effectively conflating **catalog availability / runtime registration** with **physical installation**.

### What is happening

You effectively have two different truths:

```text
Model Catalog
├── BitNet             → available/loaded
├── BGE Small          → installed
├── Qwen               → available
├── Phi                → available
├── Gemma              → available
├── Llama              → available
└── BGE Reranker       → available
```

But the runtime's in-memory registry contains references to several candidates:

```text
ExecutionRegistry._loaded_instances
        │
        ├── Phi
        ├── Gemma
        ├── Llama
        └── ...
```

Then `ModelLifecycleManager.get_status()` sees:

> "It's in `_loaded_instances` → LOADED"

without first asking:

> **"Does the model actually exist?"**

The UI then does:

```text
installed = status == INSTALLED || status == LOADED
```

Hence:

**7 ≠ 7 physical models**

It's really closer to:

**7 catalog/runtime states, 2 actual local model files.**

### The fix proposed is correct

The important invariant should be:

> **`INSTALLED` means the model artifact physically exists and passes integrity validation.**

And:

> **`LOADED` means that an installed model is currently loaded into an active execution provider.**

So the state machine should effectively be:

```text
AVAILABLE
    │
    │ install
    ▼
DOWNLOADING
    │
    │ verified
    ▼
INSTALLED
    │
    │ load
    ▼
LOADED
    │
    │ unload
    ▼
INSTALLED
```

Not:

```text
Router mentioned model
        ↓
ExecutionRegistry knows model
        ↓
LOADED
```

### One thing I would add before the agent implements it

Don't merely check:

```python
Path(model_path).exists()
```

For `INSTALLED`, ideally verify:

1. File exists
2. File size is plausible/non-zero
3. SHA-256 matches manifest when available
4. Model format is compatible
5. The model isn't merely a stale registry entry

And distinguish:

```text
CATALOG STATUS
AVAILABLE
DOWNLOADING
INSTALLED
CORRUPTED
```

from:

```text
EXECUTION STATUS
NOT_LOADED
LOADING
LOADED
FAILED
```

Then the UI can derive:

```text
Physical installation = catalog artifact state
Runtime loaded = execution state
```

This is much cleaner than stuffing everything into one `ModelStatus`.

### And this matters for your new architecture

Because your **AI Router must only select models that are actually executable**.

Imagine the router sees:

```text
Qwen = LOADED
```

but Qwen isn't actually on disk.

That's not merely a misleading dashboard number. The router can make an invalid `RoutingDecision`, which then fails at execution.

So I'd tell the agent:

> **Fix the lifecycle state model at the source, not the dashboard counter. Then make `ModelCapabilityRegistry` consume only executable/verified model states.**

That aligns directly with the architecture you just froze: Model Garden owns physical model lifecycle, while ExecutionRegistry owns active runtime state. 

**This bug is actually useful to catch now. It proves why the separation of Model Garden → Capability Registry → Execution Registry needs to be enforced in code, not merely documented.**
