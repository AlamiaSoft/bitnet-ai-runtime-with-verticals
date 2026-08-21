import pytest
from bitnet_runtime.agent.agent import Agent, AgentRunResult
from bitnet_runtime.agent.guardrails import AgentGuardrails
from bitnet_runtime.inference.mock_engine import MockInferenceEngine
from bitnet_runtime.memory.db import DatabaseManager
from bitnet_runtime.memory.episodic_memory import EpisodicMemory
from bitnet_runtime.tools.base import tool
from bitnet_runtime.tools.registry import ToolRegistry

@pytest.mark.asyncio
async def test_react_agent_execution(tmp_path):
    db = DatabaseManager(tmp_path / "agent_test.db")
    episodic = EpisodicMemory(db)

    registry = ToolRegistry()

    @tool(name="fetch_status", description="Returns system status")
    def fetch_status(service: str) -> str:
        return f"Service {service} is operational."

    registry.register(fetch_status)

    engine = MockInferenceEngine()
    # Mock ReAct sequence: 1. Tool Call, 2. Final Answer
    step1 = 'Thought: I should fetch the service status.\nAction: fetch_status\nAction Input: {"service": "payments"}'
    step2 = 'Thought: The service is operational.\nFinal Answer: Payment gateway is completely healthy.'

    responses = [step1, step2]
    def mock_handler(prompt: str) -> str:
        if "Service payments is operational" in prompt:
            return step2
        return step1

    engine.register_pattern(".*", mock_handler)

    agent = Agent(
        name="TestReActAgent",
        inference_engine=engine,
        tool_registry=registry,
        episodic_memory=episodic,
    )

    res: AgentRunResult = await agent.run("Check payments service health")
    assert res.success is True
    assert "Payment gateway is completely healthy." in res.final_answer
    assert len(res.steps) == 2
    assert res.steps[0].action == "fetch_status"

def test_guardrails():
    gr = AgentGuardrails(max_iterations=5)
    assert gr.check_iteration_limit(3) is True
    assert gr.check_iteration_limit(5) is False

    # Infinite loop detection
    assert gr.detect_infinite_loop(["search", "read", "read", "read"]) is True
    assert gr.detect_infinite_loop(["search", "read", "write"]) is False
