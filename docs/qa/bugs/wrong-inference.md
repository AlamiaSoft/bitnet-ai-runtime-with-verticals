Yes — **this is critical**, and it exposes a fundamental problem in the current Alamia Local AI Runtime inference layer.

The issue is **not merely that BitNet is "bad at arithmetic."** Look at the pattern:

| Test              | Expected |        BitNet output | Problem                  |
| ----------------- | -------: | -------------------: | ------------------------ |
| `2+2`             |        4 |             **Four** | Correct                  |
| `2+200`           |      202 |              **402** | Wrong                    |
| `are you sure?`   |        — | Generic confirmation | Failed self-verification |
| `2+200`           |      202 |              **202** | Correct                  |
| `2+200, one word` |      202 |              **402** | Wrong again              |

That inconsistency is the important part.

### What this proves

Your runtime currently appears to be treating the BitNet model as:

**prompt → raw generation → answer**

That's insufficient for a production **Local AI Runtime**.

The model can produce a plausible-looking answer while being factually wrong, and worse, **temperature/sampling/context can cause the same deterministic-looking question to produce different answers**.

The `402` answer is particularly revealing: the model appears to be pattern-generating rather than reliably executing arithmetic.

### This validates your AI Router idea

Your architecture should become something like:

```text
                    ALAMIA LOCAL AI RUNTIME
                              │
                         AI ROUTER
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        BitNet / SLM      Local GPU       Frontier
              │
              ▼
       Capability Check
              │
       ┌──────┴──────┐
       │             │
   Generation     Tool/Verifier
       │             │
       └──────┬──────┘
              ▼
        Final Response
```

For example:

**Arithmetic**
→ calculator/tool, **not BitNet**

**Embeddings**
→ embedding model

**Classification/extraction**
→ small SLM

**Simple summarization**
→ BitNet/SLM

**Coding/reasoning**
→ stronger local model/GPU

**Complex reasoning**
→ frontier model if available

### The killer product insight

Don't market this as:

> "BitNet gives you AI locally."

Market the runtime as:

> **"Alamia intelligently chooses the right local AI capability for every task."**

BitNet becomes **one component of the Model Garden**, rather than the product's brain.

And this test gives you an excellent **router evaluation suite**. Before allowing a model into production, run capability probes:

* arithmetic
* instruction following
* JSON adherence
* factual consistency
* extraction
* classification
* reasoning
* hallucination resistance
* context handling
* latency
* memory footprint

Then the router can have empirical capability scores rather than blindly sending everything to BitNet.

**Your 1-bit experiment just demonstrated why the router/runtime layer is potentially much more valuable than the model itself.**
