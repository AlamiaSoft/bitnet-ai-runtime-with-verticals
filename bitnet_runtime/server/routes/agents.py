from __future__ import annotations
from typing import Any, Dict, Optional
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

import time
from ..telemetry import telemetry_collector

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
