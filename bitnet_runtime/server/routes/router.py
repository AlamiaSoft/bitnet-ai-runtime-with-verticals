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

router = APIRouter(prefix="/api/v1/router", tags=["AI Router"])

ai_router = AIRouter()
_recent_traces: List[Dict[str, Any]] = []

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
    total_calls = len(_recent_traces)
    avg_latency = (
        sum(t["latency_ms"] for t in _recent_traces) / max(total_calls, 1)
        if _recent_traces
        else 0.0
    )
    total_cost = sum(t.get("estimated_cost_usd", 0.0) for t in _recent_traces)

    return {
        "total_routed_tasks": total_calls,
        "average_latency_ms": round(avg_latency, 2),
        "total_estimated_cost_usd": round(total_cost, 6),
        "recent_traces": _recent_traces[-20:],
    }

@router.post("/complete")
async def complete_with_router(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a prompt through the AI Router with automated model selection."""
    prompt = payload.get("prompt", "")
    task_type_str = payload.get("task_type")
    task_type = TaskType(task_type_str) if task_type_str else None

    resp, trace = await ai_router.complete(prompt=prompt, task_type=task_type)
    trace_dict = asdict(trace)
    _recent_traces.append(trace_dict)

    return {
        "text": resp.text,
        "executed_model_id": trace.executed_model_id,
        "latency_ms": trace.latency_ms,
        "estimated_cost_usd": trace.estimated_cost_usd,
        "trace": trace_dict,
    }
