from __future__ import annotations
import asyncio
import time
from typing import Any, AsyncGenerator, Dict, List, Optional
from ..config import AppConfig, config
from ..execution.registry import ExecutionRegistry, execution_registry as global_execution_registry
from ..inference.base import CompletionResponse, TokenUsage
from ..logging import logger
from .models import (
    ExecutionPlacement,
    ExecutionTarget,
    ModelCapabilityProfile,
    ModelTier,
    PrivacyRequirement,
    RoutingDecision,
    RoutingTrace,
    TaskRequirements,
    TaskType,
)
from .policy_engine import RoutingPolicyEngine
from .registry import ModelCapabilityRegistry

class AIRouter:
    """
    Core AI Router runtime service:
    - Stage 1: Evaluates task requirements & selects optimal models (Model Routing).
    - Stage 2: Resolves physical execution provider & runtime (Native CPU, in-process, GPU, Container, Remote VPS).
    - Manages automatic failover chains and timeouts.
    - Emits structured observability traces with deterministic "Why?" explanations.
    """

    def __init__(
        self,
        registry: Optional[ModelCapabilityRegistry] = None,
        policy_engine: Optional[RoutingPolicyEngine] = None,
        execution_registry: Optional[ExecutionRegistry] = None,
        runtime_resolver: Optional[Any] = None,
        endpoint_resolver: Optional[Any] = None,
        cfg: Optional[AppConfig] = None,
    ):
        self.config = cfg or config
        self.registry = registry or ModelCapabilityRegistry()
        self.policy_engine = policy_engine or RoutingPolicyEngine(self.registry)
        self.execution_registry = execution_registry or global_execution_registry
        resolver = runtime_resolver or endpoint_resolver
        if resolver is None:
            from ..execution.runtime_resolver import global_runtime_resolver
            self.runtime_resolver = global_runtime_resolver
        else:
            self.runtime_resolver = resolver
        self.endpoint_resolver = self.runtime_resolver
        self._engine_cache: Dict[str, Any] = {}

    def infer_task_requirements(self, prompt: str, task_type: Optional[TaskType] = None) -> TaskRequirements:
        """Heuristically infers task requirements. Never defaults ambiguous prompts to reasoning."""
        prompt_lower = prompt.lower().strip()
        est_tokens = len(prompt.split()) * 2

        if task_type:
            inferred_type = task_type
        # 1. Extraction
        elif any(k in prompt_lower for k in ["extract", "json", "entities", "phone", "email", "fields", "schema"]):
            inferred_type = TaskType.EXTRACTION
        # 2. Coding
        elif any(k in prompt_lower for k in ["def ", "class ", "function", "code", "bug", "syntax", "refactor", "import "]):
            inferred_type = TaskType.CODING
        # 3. Summarization
        elif any(k in prompt_lower for k in ["summarize", "briefing", "tldr", "digest", "condense"]):
            inferred_type = TaskType.SUMMARIZATION
        # 4. Explicit Classification
        elif any(k in prompt_lower for k in ["classify", "priority", "sentiment", "label", "category", "intent"]):
            inferred_type = TaskType.CLASSIFICATION
        # 5. Deep Analytical Reasoning (Strict explicit criteria)
        elif any(k in prompt_lower for k in ["step-by-step logic", "prove ", "derive ", "solve the riddle", "solve the puzzle", "root cause analysis", "complex deduction"]):
            inferred_type = TaskType.REASONING
        # 6. Default: General Dialogue & Lightweight Queries (e.g. 123, songs, questions, chat)
        else:
            inferred_type = TaskType.DIALOGUE

        return TaskRequirements(
            task_type=inferred_type,
            estimated_context_tokens=max(est_tokens, 100),
            privacy=PrivacyRequirement.AIRGAPPED_LOCAL_ONLY,
            min_quality=2.0,
        )

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        task_type: Optional[TaskType] = None,
        requirements: Optional[TaskRequirements] = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
        stop_sequences: Optional[List[str]] = None,
        timeout_seconds: float = 60.0,
    ) -> tuple[CompletionResponse, RoutingTrace]:
        """
        Routes and executes prompt completion across optimal model tiers with automated failover.
        """
        start_time = time.time()
        req = requirements or self.infer_task_requirements(prompt, task_type=task_type)
        
        # Stage 1: Model Selection
        decision = self.policy_engine.evaluate_route(req)

        # Stage 2: Initial Execution Runtime Resolution
        primary_manifest = self.registry.garden.get(decision.primary_model.model_id)
        if primary_manifest and self.runtime_resolver:
            try:
                placement = await self.runtime_resolver.resolve_execution(primary_manifest, privacy=req.privacy)
                decision.execution_placement = placement
                decision.why = f"{decision.model_selection.model_reason if decision.model_selection else decision.rationale} -> {placement.why}"
            except Exception as ex:
                logger.debug(f"Runtime resolution detail: {ex}")

        trace = RoutingTrace(
            task_requirements=req,
            decision=decision,
            why=decision.why,
        )

        candidates_to_try = [decision.primary_model] + decision.fallback_chain
        last_error = None

        for idx, candidate in enumerate(candidates_to_try):
            is_fallback = (idx > 0)
            attempt_info = {
                "candidate_id": candidate.model_id,
                "tier": str(candidate.tier),
                "is_fallback": is_fallback,
                "timestamp": time.time(),
            }

            try:
                t_call_start = time.time()
                current_placement = None
                manifest = self.registry.garden.get(candidate.model_id)
                if manifest and self.runtime_resolver:
                    current_placement = await self.runtime_resolver.resolve_execution(manifest, privacy=req.privacy)
                    attempt_info["runtime_type"] = current_placement.runtime_type.value
                    attempt_info["execution_target"] = current_placement.target.value
                    attempt_info["endpoint_url"] = current_placement.endpoint_url
                    attempt_info["endpoint_label"] = current_placement.endpoint_label

                if candidate.provider in self._engine_cache:
                    engine = self._engine_cache[candidate.provider]
                    resp = await asyncio.wait_for(
                        engine.complete(
                            prompt=prompt,
                            system_prompt=system_prompt,
                            temperature=temperature,
                            max_tokens=max_tokens,
                            stop_sequences=stop_sequences,
                        ),
                        timeout=timeout_seconds,
                    )
                else:
                    if not manifest:
                        raise RuntimeError(f"Manifest for '{candidate.model_id}' not found in Model Garden.")

                    resp = await asyncio.wait_for(
                        self.execution_registry.complete(
                            manifest=manifest,
                            prompt=prompt,
                            system_prompt=system_prompt,
                            temperature=temperature,
                            max_tokens=max_tokens,
                            stop_sequences=stop_sequences,
                            endpoint_url=current_placement.endpoint_url if current_placement else None,
                        ),
                        timeout=timeout_seconds,
                    )

                t_call_end = time.time()
                call_duration_ms = (t_call_end - t_call_start) * 1000.0

                # Compute cost estimate
                input_tokens = resp.usage.prompt_tokens if resp.usage else len(prompt.split())
                output_tokens = resp.usage.completion_tokens if resp.usage else len(resp.text.split())
                cost = (input_tokens / 1000.0 * candidate.cost_per_1k_input) + (output_tokens / 1000.0 * candidate.cost_per_1k_output)

                attempt_info["success"] = True
                attempt_info["duration_ms"] = round(call_duration_ms, 2)
                trace.attempts.append(attempt_info)

                loaded_inst = self.execution_registry._loaded_instances.get(candidate.model_id) if hasattr(self, "execution_registry") and self.execution_registry else None
                if candidate.provider not in self._engine_cache and manifest.provider_backend != "bitnet" and loaded_inst and str(loaded_inst.backend_type.value).replace("-", "_") == "bitnet_sidecar":
                    trace.fallback_invoked = True
                    trace.executed_model_id = "bitnet_b1_58_2b"
                    trace.runtime_type = current_placement.runtime_type if current_placement else RuntimeType.NATIVE_CPU
                    trace.execution_target = current_placement.target if current_placement else ExecutionTarget.LOCAL_CPU_CONTAINER
                    trace.endpoint = current_placement.endpoint_label if current_placement else "BitNet Native (Local)"
                    trace.why = f"Task '{req.task_type.value}' (Requested: {candidate.name} - not installed) -> Failover to BitNet b1.58 2B -> {trace.endpoint}"
                    if trace.decision:
                        trace.decision.rationale = f"Executed on BitNet b1.58 2B (failover: {candidate.name} is not installed locally)"
                else:
                    trace.executed_model_id = candidate.model_id
                    trace.fallback_invoked = is_fallback or (candidate.model_id != decision.primary_model.model_id)
                    trace.endpoint = current_placement.endpoint_label if current_placement else "Native In-Process GGUF (CPU)"
                    trace.runtime_type = current_placement.runtime_type if current_placement else None
                    trace.execution_target = current_placement.target if current_placement else None
                    trace.why = decision.why or f"Task '{req.task_type.value}' executed on {trace.executed_model_id} via {trace.endpoint}"

                trace.latency_ms = round((time.time() - start_time) * 1000.0, 2)
                trace.token_usage = resp.usage
                trace.estimated_cost_usd = round(cost, 6)
                trace.success = True

                logger.debug(
                    f"Router completed task '{req.task_type}' on '{trace.executed_model_id}' via '{trace.endpoint}' "
                    f"in {trace.latency_ms}ms (Cost: ${trace.estimated_cost_usd:.6f})"
                )
                return resp, trace

            except Exception as e:
                attempt_info["success"] = False
                attempt_info["error"] = str(e)
                trace.attempts.append(attempt_info)
                last_error = e
                logger.warning(
                    f"Model '{candidate.model_id}' failed execution ({e}). Invoking next fallback candidate..."
                )
                # Mark health degraded
                self.registry.update_health(candidate.model_id, False)

        # If all candidates failed
        trace.success = False
        trace.error = f"All candidate models failed in routing chain. Last error: {last_error}"
        trace.latency_ms = round((time.time() - start_time) * 1000.0, 2)
        raise RuntimeError(trace.error)
