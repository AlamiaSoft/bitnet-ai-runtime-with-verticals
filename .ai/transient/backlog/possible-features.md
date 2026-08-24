# Backlog: Future Architectural Proposals & Evolution Engine

See detailed documentation in `docs/possible-features.md`.

## 1. Alamia Evolution Engine (Self-Improving Agent Architecture)
- **Subsystem**: `bitnet_runtime/evolution/`
- **Modules**:
  - `ExperienceCollector`: Capture execution traces, tool outcomes, and user feedback.
  - `OutcomeEvaluator`: Deterministic criteria and schema validation.
  - `StrategyOptimizer`: Candidate mutation generation.
  - `SandboxBenchmark`: Probe test execution comparing v1 vs v2.
  - `PromotionGate`: Regression-free promotion to active persona.

## 2. Deterministic Arithmetic Routing & Math Verifiers
- Detect arithmetic operations in `AIRouter.infer_task_requirements()`.
- Short-circuit directly to `CalculatorTool` / Python execution to eliminate SLM numerical hallucinations.

## 3. Empirical Model Probing Suite
- Benchmark host models for arithmetic accuracy, JSON conformance, negative constraint compliance, extraction accuracy, and latency/RAM envelopes.
