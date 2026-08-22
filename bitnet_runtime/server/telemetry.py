from __future__ import annotations
import datetime
import time
import uuid
from dataclasses import asdict
from typing import Any, Dict, List, Optional
from ..router.models import RoutingTrace

class TelemetryCollector:
    """
    Centralized telemetry service tracking all model executions,
    prompts, generated outputs, router decisions, latency percentiles, and cost savings.
    """

    def __init__(self):
        self._traces: List[Dict[str, Any]] = []

    def record_trace(
        self,
        trace: RoutingTrace,
        prompt: str = "",
        response_text: str = "",
    ) -> None:
        trace_dict = asdict(trace)
        trace_dict["prompt"] = prompt
        trace_dict["response_text"] = response_text
        trace_dict["timestamp_str"] = datetime.datetime.now().strftime("%H:%M:%S")
        self._traces.append(trace_dict)
        if len(self._traces) > 500:
            self._traces.pop(0)

    def record_direct_chat(
        self,
        model_id: str,
        prompt: str,
        response_text: str,
        latency_ms: float,
        tokens_used: int,
        cost_usd: float = 0.0,
        task_type: str = "interactive_chat",
    ) -> None:
        entry = {
            "trace_id": f"chat_{uuid.uuid4().hex[:8]}",
            "timestamp": time.time(),
            "timestamp_str": datetime.datetime.now().strftime("%H:%M:%S"),
            "prompt": prompt,
            "response_text": response_text,
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
            "recent_traces": list(reversed(self._traces[-30:])),
        }

telemetry_collector = TelemetryCollector()
