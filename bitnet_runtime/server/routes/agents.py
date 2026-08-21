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

@router.post("/run", response_model=AgentRunResponse)
async def run_agent(req: AgentRunRequest):
    agent, _ = get_agent_dependencies()

    async def on_event(event: Dict[str, Any]):
        await broadcaster.broadcast({"session_id": req.session_id, **event})

    res: AgentRunResult = await agent.run(req.prompt, session_id=req.session_id, event_callback=on_event)
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
