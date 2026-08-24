# Possible Features & Future Architectural Proposals

This document captures candidate features, architectural enhancements, and experimental capabilities under evaluation for future development cycles.

---

## 1. Deterministic Tool Routing & Math Verifiers (Arithmetic Guardrails)

### Context & Problem Statement
Small Language Models (SLMs) such as 1-bit / 2B ternary models excel at classification, extraction, semantic summarization, and local dialogue triage. However, neural autoregressive architectures are inherently statistical next-token estimators and suffer from arithmetic inconsistency on direct multi-digit operations (e.g. 2+200 outputting 402).

### Proposed Solution
Transition from raw generation (Prompt -> LLM -> Output) to an intelligent capability-aware routing pipeline:

```
                    ALAMIA LOCAL AI RUNTIME
                               |
                           AI ROUTER
                               |
               +---------------+---------------+
               |                               |
       [Deterministic Task]            [Generative Task]
               |                               |
        Tool / Verifier                   Model Garden
        (e.g., Python Math,                    |
         Date/Time Parser,              Capability Check
         Unit Converter)                (BitNet / SLM / GPU)
               |                               |
               +---------------+---------------+
                               |
                         Final Response
```

### Key Modules to Implement:
1. **Arithmetic & Logic Classifier**:
   - Detect explicit math operations (e.g., `2+200`, `15% of 3000`, date calculations) in `AIRouter.infer_task_requirements()`.
   - Short-circuit or augment prompt with deterministic tool executions (`CalculatorTool` / Python `ast` evaluation).
2. **Deterministic Output Verifier**:
   - Inspect generative responses that claim numerical calculations and verify against deterministic arithmetic results before returning to user.

---

## 2. Empirical Model Capability Probing Suite

### Context
Currently, model task ratings in the Model Garden are initialized from catalog benchmarks and static metadata. In an enterprise local runtime, models should be empirically scored on the actual host hardware and quantized weights.

### Proposed Solution
Add an automated **Model Capability Probe Engine** that benchmarks installed models against a standardized local evaluation test suite:

- **Arithmetic & Logic Accuracy**: Multi-digit additions, multiplications, percentage calculations.
- **Instruction Following**: Negative constraints ("answer in one word", "do not mention X").
- **Structured Output / JSON Adherence**: Schema conformance and valid JSON syntax under zero-shot prompting.
- **Factual & Contextual Consistency**: Hallucination resistance on closed-context QA.
- **Extraction Accuracy**: Entity extraction (emails, phone numbers, order IDs) from messy text.
- **Hardware Latency & Memory Envelope**: Real tokens/sec, time-to-first-token (TTFT), and RAM consumption.

The generated empirical scores dynamically update `ModelCapabilityProfile.task_ratings` in the AI Router.

---

## 3. Multi-Step Self-Verification & Guardrail Pipelines

### Context
When complex reasoning or critical operations are required (such as in the AI Employee or Financial Analysis verticals), single-pass generation can yield subtle errors.

### Proposed Solution
1. **Draft -> Critique -> Refine Loop**:
   - Generate initial candidate response with high-speed SLM (`BitNet`).
   - Run lightweight verification pass with persona-learned guidelines and rule invariants.
   - Return verified response or flag for Human-in-the-Loop approval.
2. **Automated Unit Test Verifier for Code Generation**:
   - When generating code, spin up an isolated scratch runner to execute syntax and unit tests before displaying code to the operator.

---

## 4. Hardware-Aware Model Sharding & Multi-Model Ensembles

### Context
Edge devices often have asymmetric compute (e.g., 8-core CPU with 32GB RAM + low-power NPU/iGPU).

### Proposed Solution
- **Hierarchical Model Cascades**: Route simple queries to 1-bit CPU BitNet models; seamlessly escalate difficult reasoning steps to larger quantized dense models (e.g., LLaMA 3.2 3B or Gemma 2 2B) or local GPU backends when available.
- **Parallel Speculative Decoding**: Use 1-bit BitNet as a draft model to accelerate token generation of larger 3B/8B dense models on local hardware.
