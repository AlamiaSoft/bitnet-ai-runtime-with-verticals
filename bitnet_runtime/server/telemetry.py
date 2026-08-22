from __future__ import annotations
import time
import uuid
from dataclasses import asdict
from typing import Any, Dict, List, Optional
from ..router.models import RoutingTrace

class TelemetryCollector:
    """
    Centralized telemetry service tracking all model executions,
    router decisions, playground chats, latency percentiles, and cost savings.
    """

    def __init__(self):
        self._traces: List[Dict[str, Any]] = []

    def record_trace(self, trace: RoutingTrace) -> None:
        trace_dict = asdict(trace)
        self._traces.append(trace_dict)
        if len(self._traces) > 500:
            self._traces.pop(0)

    def record_direct_chat(
        self,
        model_id: str,
        latency_ms: float,
        tokens_used: int,
        cost_usd: float = 0.0,
        task_type: str = "interactive_chat",
    ) -> None:
        entry = {
            "trace_id": f"chat_{uuid.uuid4().hex[:8]}",
            "timestamp": time.time(),
            "task_requirements": {"task_type": task_type},
            "decision": {
                "primary_model": {"model_id": model_id},
                "rationale": f"Direct user interaction with {model_id} via Model Playground.",
                "candidate_scores": {model_id: 100.0},
            },
            "executed_model_id": model_id,
            "fallback_invoked": False,
            "latency_ms": latency_ms,
            "token_usage": {"total_tokens": tokens_used},
            "estimated_cost_usd": cost_usd,
            "success": True,
        }
        self._traces.append(entry)
        if len(self._traces) > 500:
            self._traces.pop(0)

    def get_summary(self) -> Dict[str, Any]:
        total_calls = len(self._traces)
        avg_latency = (
            sum(t.get("latency_ms", 0.0) for t in self._traces) / max(total_calls, 1)
            if self._traces
            else 0.0
        )
        total_cost = sum(t.get("estimated_cost_usd", 0.0) for t in self._traces)

        return {
            "total_routed_tasks": total_calls,
            "average_latency_ms": round(avg_latency, 2),
            "total_estimated_cost_usd": round(total_cost, 6),
            "recent_traces": list(reversed(self._traces[-20:])),
        }

telemetry_collector = TelemetryCollector()
