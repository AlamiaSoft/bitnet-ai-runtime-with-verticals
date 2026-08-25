from __future__ import annotations
import json
from dataclasses import asdict
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from ...router import (
    AIRouter,
    ModelCapabilityRegistry,
    ModelTier,
    PrivacyRequirement,
    RoutingPolicyEngine,
    TaskRequirements,
    TaskType,
)

from ..telemetry import telemetry_collector

router = APIRouter(prefix="/api/v1/router", tags=["AI Router"])

ai_router = AIRouter()

@router.get("/policies")
async def get_routing_policies() -> Dict[str, Any]:
    """Get current routing configuration and policy knobs."""
    return {
        "privacy_policy": "airgapped_local_only",
        "default_preferred_tier": "local_1bit",
        "zero_budget_enforced": True,
        "max_context_tokens_default": 4096,
    }

@router.post("/policies")
async def update_routing_policies(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Update routing configuration dynamically."""
    return {"status": "updated", "policies": payload}

@router.get("/telemetry")
async def get_router_telemetry() -> Dict[str, Any]:
    """Get telemetry statistics, recent routing decisions, and cost metrics."""
    return telemetry_collector.get_summary()

@router.post("/complete")
async def complete_with_router(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a prompt through the AI Router with automated model selection."""
    prompt = payload.get("prompt", "")
    task_type_str = payload.get("task_type")
    task_type = TaskType(task_type_str) if task_type_str else None

    resp, trace = await ai_router.complete(prompt=prompt, task_type=task_type)
    telemetry_collector.record_trace(trace, prompt=prompt, response_text=resp.text)

    endpoint_desc = trace.endpoint or "Native In-Process GGUF (CPU)"
    runtime_type = trace.runtime_type.value if trace.runtime_type and hasattr(trace.runtime_type, "value") else str(trace.runtime_type or "")
    execution_target = trace.execution_target.value if trace.execution_target and hasattr(trace.execution_target, "value") else str(trace.execution_target or "")
    
    decision = trace.decision
    model_reason = decision.model_selection.model_reason if decision and decision.model_selection else None
    execution_reason = decision.execution_placement.reason if decision and decision.execution_placement else None
    why = trace.why or (decision.why if decision else "")

    return {
        "text": resp.text,
        "executed_model_id": trace.executed_model_id,
        "latency_ms": trace.latency_ms,
        "estimated_cost_usd": trace.estimated_cost_usd,
        "endpoint": endpoint_desc,
        "runtime_type": runtime_type,
        "execution_target": execution_target,
        "model_reason": model_reason,
        "execution_reason": execution_reason,
        "why": why,
        "trace": asdict(trace),
    }
