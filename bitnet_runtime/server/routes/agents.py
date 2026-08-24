from __future__ import annotations
import time
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from ...agent.agent import Agent, AgentRunResult
from ...config import config
from ...inference.model_manager import ModelManager
from ...memory.db import DatabaseManager
from ...memory.episodic_memory import EpisodicMemory
from ...memory.semantic_memory import SemanticMemory
from ...tools.filesystem_tool import get_filesystem_tools
from ...tools.registry import ToolRegistry
from ...tools.shell_tool import RunShellTool
from ..sse import broadcaster
from ..telemetry import telemetry_collector
from verticals.ai_employee.worker import AIEmployeeWorker
from verticals.ai_employee.approval import ApprovalStatus
from verticals.ai_employee.personas import EMPLOYEE_PERSONAS

router = APIRouter(prefix="/agents", tags=["Agents"])

class AgentRunRequest(BaseModel):
    prompt: str
    session_id: Optional[str] = None

class AgentRunResponse(BaseModel):
    session_id: str
    success: bool
    final_answer: str
    total_iterations: int
    error: Optional[str] = None

class EmployeeTaskRequest(BaseModel):
    task: str
    user_feedback: Optional[str] = None

class EmployeeFeedbackRequest(BaseModel):
    task: str
    user_correction: str
    task_type: Optional[str] = "general"

class ApprovalResolveRequest(BaseModel):
    approved: bool
    feedback_notes: Optional[str] = None

def get_agent_dependencies():
    db = DatabaseManager(config.memory.db_path)
    model_mgr = ModelManager(config.inference)
    inf_engine = model_mgr.get_inference_engine()
    emb_engine = model_mgr.get_embedding_engine(config.memory.vector_dim)

    episodic = EpisodicMemory(db)
    semantic = SemanticMemory(db, emb_engine)

    registry = ToolRegistry()
    registry.register_many(get_filesystem_tools(config.agent.working_dir))
    if config.agent.enable_shell:
        registry.register(RunShellTool(config.agent.working_dir))

    agent = Agent(
        name="BitNetDefaultAgent",
        inference_engine=inf_engine,
        tool_registry=registry,
        episodic_memory=episodic,
        semantic_memory=semantic,
    )
    return agent, episodic

def get_employee_worker() -> AIEmployeeWorker:
    db = DatabaseManager(config.memory.db_path)
    model_mgr = ModelManager(config.inference)
    inf_engine = model_mgr.get_inference_engine()
    return AIEmployeeWorker(cfg=config, db=db, inference_engine=inf_engine)

@router.post("/run", response_model=AgentRunResponse)
async def run_agent(req: AgentRunRequest):
    agent, _ = get_agent_dependencies()
    start_time = time.time()

    async def on_event(event: Dict[str, Any]):
        await broadcaster.broadcast({"session_id": req.session_id, **event})
        if event.get("type") == "tool_call":
            telemetry_collector.record_tool_call(
                tool_name=event.get("tool_name", "Tool"),
                arguments=event.get("tool_args", {}),
                result_summary=str(event.get("tool_result", ""))[:140],
                latency_ms=event.get("latency_ms", 0.0),
                success=event.get("status") != "error",
                session_id=req.session_id,
            )

    res: AgentRunResult = await agent.run(req.prompt, session_id=req.session_id, event_callback=on_event)
    latency_ms = round((time.time() - start_time) * 1000.0, 1)

    telemetry_collector.record_agent_run(
        agent_name=agent.name,
        prompt=req.prompt,
        final_answer=res.final_answer,
        iterations=res.total_iterations,
        success=res.success,
        error=res.error,
        latency_ms=latency_ms,
        session_id=res.session_id,
    )

    return AgentRunResponse(
        session_id=res.session_id,
        success=res.success,
        final_answer=res.final_answer,
        total_iterations=res.total_iterations,
        error=res.error,
    )

@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    _, episodic = get_agent_dependencies()
    history = episodic.get_session_history(session_id)
    return {"session_id": session_id, "events": history}

# --- AI Employees Endpoints ---

@router.get("/employees")
async def list_employees():
    worker = get_employee_worker()
    personas = worker.list_personas()
    return {
        "employees": [
            {
                "id": p.id,
                "name": p.name,
                "role": p.role,
                "department": p.department,
                "avatar_initials": p.avatar_initials,
                "responsibilities": p.responsibilities,
                "skills": p.skills,
                "tools": p.tools,
                "allowed_actions": p.allowed_actions,
                "approval_required_actions": p.approval_required_actions,
                "denied_actions": p.denied_actions,
                "kpis": [
                    {"metric_name": k.metric_name, "target_value": k.target_value, "current_value": k.current_value}
                    for k in p.kpis
                ],
                "learned_rules_count": len(worker.self_learning.list_learnings_for_employee(p.id)),
            }
            for p in personas
        ]
    }

@router.get("/employees/{employee_id}")
async def get_employee_detail(employee_id: str):
    worker = get_employee_worker()
    if employee_id not in EMPLOYEE_PERSONAS:
        raise HTTPException(status_code=404, detail=f"Employee '{employee_id}' not found.")
    p = worker.get_persona(employee_id)
    learnings = worker.self_learning.list_learnings_for_employee(employee_id)
    return {
        "id": p.id,
        "name": p.name,
        "role": p.role,
        "department": p.department,
        "avatar_initials": p.avatar_initials,
        "system_prompt": p.system_prompt,
        "responsibilities": p.responsibilities,
        "skills": p.skills,
        "tools": p.tools,
        "allowed_actions": p.allowed_actions,
        "approval_required_actions": p.approval_required_actions,
        "denied_actions": p.denied_actions,
        "kpis": [
            {"metric_name": k.metric_name, "target_value": k.target_value, "current_value": k.current_value}
            for k in p.kpis
        ],
        "learned_rules": [
            {
                "id": l.id,
                "rule_text": l.rule_text,
                "trigger_pattern": l.trigger_pattern,
                "rule_type": l.rule_type,
                "confidence": l.confidence,
                "times_applied": l.times_applied,
                "created_at": l.created_at,
            }
            for l in learnings
        ],
    }

@router.post("/employees/{employee_id}/task")
async def run_employee_task(employee_id: str, req: EmployeeTaskRequest):
    worker = get_employee_worker()
    if employee_id not in EMPLOYEE_PERSONAS:
        raise HTTPException(status_code=404, detail=f"Employee '{employee_id}' not found.")

    res = await worker.execute_employee_task(
        employee_id=employee_id,
        task_prompt=req.task,
        user_feedback=req.user_feedback,
    )

    telemetry_collector.record_agent_run(
        agent_name=res["employee_name"],
        prompt=req.task,
        final_answer=res["result"],
        iterations=1,
        success=True,
        error=None,
        latency_ms=res["latency_ms"],
        session_id=f"emp_{employee_id}",
    )

    return res

@router.get("/employees/{employee_id}/learnings")
async def get_employee_learnings(employee_id: str):
    worker = get_employee_worker()
    learnings = worker.self_learning.list_learnings_for_employee(employee_id)
    return {"employee_id": employee_id, "learnings": learnings}

@router.post("/employees/{employee_id}/feedback")
async def submit_employee_feedback(employee_id: str, req: EmployeeFeedbackRequest):
    worker = get_employee_worker()
    if employee_id not in EMPLOYEE_PERSONAS:
        raise HTTPException(status_code=404, detail=f"Employee '{employee_id}' not found.")

    rule = worker.self_learning.ingest_user_feedback(
        employee_id=employee_id,
        task=req.task,
        user_correction=req.user_correction,
        task_type=req.task_type or "general",
    )
    return {"status": "learned", "rule": rule}

@router.get("/approvals")
async def list_approvals(employee_id: Optional[str] = None, status: Optional[str] = None):
    worker = get_employee_worker()
    st = ApprovalStatus(status) if status else None
    requests = worker.approval_gates.list_requests(employee_id=employee_id, status=st)
    return {"approvals": requests}

@router.post("/approvals/{request_id}/resolve")
async def resolve_approval(request_id: str, req: ApprovalResolveRequest):
    worker = get_employee_worker()
    resolved = worker.approval_gates.resolve_approval(
        request_id=request_id,
        approved=req.approved,
        feedback_notes=req.feedback_notes,
    )
    if not resolved:
        raise HTTPException(status_code=404, detail=f"Approval request '{request_id}' not found.")
    return {"status": "resolved", "approval": resolved}
