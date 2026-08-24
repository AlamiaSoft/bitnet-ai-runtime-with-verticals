from __future__ import annotations
import datetime
import time
import uuid
from dataclasses import asdict
from typing import Any, Dict, List, Optional
from ..router.models import RoutingTrace

class TelemetryCollector:
    """
    Centralized telemetry and activity audit log tracking all model executions,
    direct chats, router decisions, AI Agent runs, tool executions, and lifecycle events.
    """

    def __init__(self):
        self._traces: List[Dict[str, Any]] = []

    def _format_time(self) -> str:
        return datetime.datetime.now().strftime("%I:%M:%S %p")

    def record_trace(
        self,
        trace: RoutingTrace,
        prompt: str = "",
        response_text: str = "",
    ) -> None:
        trace_dict = asdict(trace)
        trace_dict["id"] = f"act_{uuid.uuid4().hex[:8]}"
        trace_dict["trace_id"] = trace.trace_id or f"trace_{uuid.uuid4().hex[:8]}"
        trace_dict["timestamp"] = time.time()
        trace_dict["timestamp_str"] = self._format_time()
        trace_dict["category"] = "router"
        task_name = trace.task_requirements.task_type.value if hasattr(trace.task_requirements, "task_type") else "reasoning"
        trace_dict["task_type"] = task_name
        trace_dict["title"] = f"AI Router: {task_name.replace('_', ' ').capitalize()}"
        trace_dict["target"] = trace.executed_model_id
        trace_dict["input_summary"] = (prompt[:140] + "...") if len(prompt) > 140 else prompt
        trace_dict["output_summary"] = (response_text[:140] + "...") if len(response_text) > 140 else response_text
        trace_dict["prompt"] = prompt
        trace_dict["response_text"] = response_text
        trace_dict["status"] = "success" if trace.success else "error"
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
        task_type: str = "chat",
        model_name: Optional[str] = None,
    ) -> None:
        name = model_name or model_id
        entry = {
            "id": f"act_{uuid.uuid4().hex[:8]}",
            "trace_id": f"chat_{uuid.uuid4().hex[:8]}",
            "timestamp": time.time(),
            "timestamp_str": self._format_time(),
            "category": "chat",
            "task_type": task_type,
            "title": f"Chat with {name}",
            "model_id": model_id,
            "executed_model_id": model_id,
            "target": name,
            "input_summary": (prompt[:140] + "...") if len(prompt) > 140 else prompt,
            "output_summary": (response_text[:140] + "...") if len(response_text) > 140 else response_text,
            "prompt": prompt,
            "response_text": response_text,
            "task_requirements": {"task_type": task_type},
            "decision": {
                "primary_model": {"model_id": model_id},
                "rationale": f"Direct interaction with {name} via Model Playground.",
                "candidate_scores": {model_id: 100.0},
            },
            "fallback_invoked": False,
            "latency_ms": latency_ms,
            "token_usage": {"total_tokens": tokens_used},
            "tokens": tokens_used,
            "estimated_cost_usd": cost_usd,
            "status": "success",
            "success": True,
        }
        self._traces.append(entry)
        if len(self._traces) > 500:
            self._traces.pop(0)

    def record_agent_run(
        self,
        agent_name: str,
        prompt: str,
        final_answer: str,
        iterations: int,
        success: bool,
        error: Optional[str] = None,
        latency_ms: float = 0.0,
        session_id: Optional[str] = None,
    ) -> None:
        entry = {
            "id": f"act_{uuid.uuid4().hex[:8]}",
            "trace_id": f"agent_{uuid.uuid4().hex[:8]}",
            "timestamp": time.time(),
            "timestamp_str": self._format_time(),
            "category": "agent",
            "task_type": "autonomous_agent",
            "title": f"AI Employee: {agent_name}",
            "target": agent_name,
            "executed_model_id": "BitNet Agent",
            "input_summary": (prompt[:140] + "...") if len(prompt) > 140 else prompt,
            "output_summary": (final_answer[:140] + "...") if len(final_answer) > 140 else (error or "Execution completed"),
            "prompt": prompt,
            "response_text": final_answer,
            "session_id": session_id,
            "iterations": iterations,
            "latency_ms": latency_ms,
            "estimated_cost_usd": 0.0,
            "status": "success" if success else "error",
            "success": success,
        }
        self._traces.append(entry)
        if len(self._traces) > 500:
            self._traces.pop(0)

    def record_tool_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        result_summary: str,
        latency_ms: float = 0.0,
        success: bool = True,
        session_id: Optional[str] = None,
    ) -> None:
        entry = {
            "id": f"act_{uuid.uuid4().hex[:8]}",
            "trace_id": f"tool_{uuid.uuid4().hex[:8]}",
            "timestamp": time.time(),
            "timestamp_str": self._format_time(),
            "category": "tool",
            "task_type": "tool_execution",
            "title": f"Tool Execution: {tool_name}",
            "target": tool_name,
            "executed_model_id": tool_name,
            "input_summary": str(arguments)[:140],
            "output_summary": result_summary[:140],
            "session_id": session_id,
            "latency_ms": latency_ms,
            "estimated_cost_usd": 0.0,
            "status": "success" if success else "error",
            "success": success,
        }
        self._traces.append(entry)
        if len(self._traces) > 500:
            self._traces.pop(0)

    def record_model_lifecycle(
        self,
        action: str,
        model_id: str,
        model_name: Optional[str] = None,
        ram_mb: Optional[float] = None,
        status: str = "success",
        latency_ms: float = 0.0,
    ) -> None:
        name = model_name or model_id
        action_verb = "Loaded" if action == "load" else "Unloaded" if action == "unload" else "Installed" if action == "install" else action.capitalize()
        entry = {
            "id": f"act_{uuid.uuid4().hex[:8]}",
            "trace_id": f"life_{uuid.uuid4().hex[:8]}",
            "timestamp": time.time(),
            "timestamp_str": self._format_time(),
            "category": "model_lifecycle",
            "task_type": f"model_{action}",
            "title": f"{action_verb} {name}",
            "model_id": model_id,
            "executed_model_id": model_id,
            "target": name,
            "input_summary": f"Lifecycle transition: {action} on {model_id}",
            "output_summary": f"Status: {status}" + (f", Allocated RAM: {ram_mb:.1f} MB" if ram_mb else ""),
            "latency_ms": latency_ms,
            "estimated_cost_usd": 0.0,
            "status": "success" if status in ("success", "loaded", "unloaded", "installed") else "error",
            "success": status in ("success", "loaded", "unloaded", "installed"),
        }
        self._traces.append(entry)
        if len(self._traces) > 500:
            self._traces.pop(0)

    def record_embedding(
        self,
        model_id: str,
        text_a: str,
        text_b: str,
        similarity: float,
        latency_ms: float,
    ) -> None:
        entry = {
            "id": f"act_{uuid.uuid4().hex[:8]}",
            "trace_id": f"embed_{uuid.uuid4().hex[:8]}",
            "timestamp": time.time(),
            "timestamp_str": self._format_time(),
            "category": "embedding",
            "task_type": "embedding",
            "title": f"Vector Embedding & Cosine Similarity",
            "model_id": model_id,
            "executed_model_id": model_id,
            "target": model_id,
            "input_summary": f"Text A: '{text_a[:60]}' | Text B: '{text_b[:60]}'",
            "output_summary": f"Cosine similarity score: {similarity:.4f}",
            "latency_ms": latency_ms,
            "estimated_cost_usd": 0.0,
            "status": "success",
            "success": True,
        }
        self._traces.append(entry)
        if len(self._traces) > 500:
            self._traces.pop(0)

    def record_memory_event(
        self,
        action: str,
        detail: str,
        result_count: int = 0,
        latency_ms: float = 0.0,
    ) -> None:
        entry = {
            "id": f"act_{uuid.uuid4().hex[:8]}",
            "trace_id": f"mem_{uuid.uuid4().hex[:8]}",
            "timestamp": time.time(),
            "timestamp_str": self._format_time(),
            "category": "memory",
            "task_type": f"memory_{action}",
            "title": f"Memory OS: {action.replace('_', ' ').capitalize()}",
            "target": "Personal Memory OS",
            "executed_model_id": "Vector Database",
            "input_summary": detail[:140],
            "output_summary": f"Matches / records: {result_count}",
            "latency_ms": latency_ms,
            "estimated_cost_usd": 0.0,
            "status": "success",
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

        recent = list(reversed(self._traces[-50:]))
        return {
            "total_routed_tasks": total_calls,
            "total_executions": total_calls,
            "average_latency_ms": round(avg_latency, 2),
            "total_estimated_cost_usd": round(total_cost, 6),
            "recent_traces": recent,
            "traces": recent,
        }

telemetry_collector = TelemetryCollector()
