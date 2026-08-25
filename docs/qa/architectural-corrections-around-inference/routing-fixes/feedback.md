Yes — **routing is still wrong in two important ways.**

| Problem                                    | Evidence                                                                                      | Fix                                                                                                                                             |
| ------------------------------------------ | --------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| **1. Task classification is wrong**        | `123` → `reasoning`; song recommendation → `reasoning`                                        | Add/strengthen `simple_chat`, `general_knowledge`, `recommendation`, `calculation` task classes. Don't default ambiguous prompts to reasoning.  |
| **2. Model selection is wrong**            | Romantic songs → **Mock Development Engine / 1-bit**                                          | Mock engine must **never be a production candidate**. Mark it `development_only` and exclude from router selection.                             |
| **3. Telemetry contradicts execution**     | `mock_local_engine` but explanation says `Model 'Mock Development Engine'` / BitNet container | Ensure displayed model, runtime, endpoint and actual executor come from the **same final execution result**, not separate metadata paths.       |
| **4. Container still appears prominently** | `BitNet Container (11434)`                                                                    | If native/in-process runtime exists, container should not win merely because it's healthy. Runtime capability + preference must determine this. |
| **5. 8 sec for simple request**            | `8087ms` for song recommendation                                                              | Routing/inference overhead is excessive. Simple tasks should preferentially use the smallest/fastest suitable model.                            |
| **6. Hallucinated music facts**            | `"Jai Ho" (Begum Devi)`, etc.                                                                 | This is a **model-quality/routing problem**. A 1-bit/weak model shouldn't handle factual recommendation tasks where accuracy matters.           |

### The biggest fix

Your router currently appears to optimize around:

> **"Which model has the best benchmark rating for this task?"**

It needs to optimize around:

> **"What is the cheapest/fastest model that is actually capable of this task?"**

For these examples:

```text
123
→ calculation/simple input
→ tiny fast model / calculator
→ NOT reasoning
```

```text
3 romantic Indian songs
→ recommendation/general knowledge
→ capable SLM/local model
→ NOT Mock Development Engine
→ optionally web/search if factual freshness matters
```

And **Mock Development Engine should disappear completely from normal Model Garden routing**. It is a test fixture, not a model.

One more important rule: **`reasoning` should become a high-cost/high-capability classification, not the default bucket for anything that isn't explicitly recognized.**
