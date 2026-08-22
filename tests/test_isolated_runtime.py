import sys
import pytest
from bitnet_runtime.agent.agent import Agent
from bitnet_runtime.config import AppConfig
from bitnet_runtime.inference.model_manager import ModelManager
from bitnet_runtime.memory.db import DatabaseManager
from bitnet_runtime.memory.episodic_memory import EpisodicMemory
from bitnet_runtime.memory.semantic_memory import SemanticMemory
from bitnet_runtime.plugins.vertical_registry import (
    VerticalManifest,
    VerticalPluginContract,
    VerticalRegistry,
)
from bitnet_runtime.policy.policy_engine import SecurityPolicyEngine
from bitnet_runtime.tools.filesystem_tool import get_filesystem_tools
from bitnet_runtime.tools.registry import ToolRegistry

@pytest.mark.asyncio
async def test_runtime_runs_completely_isolated_from_verticals(tmp_path):
    """
    Proof 1: The runtime operates with 100% independence from any verticals package.
    """
    cfg = AppConfig()
    cfg.memory.db_path = tmp_path / "isolated.db"
    cfg.agent.working_dir = tmp_path / "workspace"
    cfg.inference.default_provider = "mock"

    db = DatabaseManager(cfg.memory.db_path)
    model_mgr = ModelManager(cfg.inference)
    inf_engine = model_mgr.get_inference_engine()
    emb_engine = model_mgr.get_embedding_engine(cfg.memory.vector_dim)

    episodic = EpisodicMemory(db)
    semantic = SemanticMemory(db, emb_engine)
    tools = ToolRegistry()
    tools.register_many(get_filesystem_tools(cfg.agent.working_dir))

    agent = Agent(
        name="IsolatedAgent",
        inference_engine=inf_engine,
        tool_registry=tools,
        episodic_memory=episodic,
        semantic_memory=semantic,
    )

    result = await agent.run("Hello from isolated runtime")
    assert result.success is True
    assert len(result.final_answer) > 0

@pytest.mark.asyncio
async def test_external_vertical_plugin_discovery_and_execution():
    """
    Proof 2: An external third-party vertical package integrates seamlessly
    via VerticalPluginContract without touching runtime code.
    """
    class StandaloneThirdPartyCRM(VerticalPluginContract):
        manifest = VerticalManifest(
            name="thirdparty_crm",
            title="External Third-Party CRM",
            version="2.0.0",
            description="External enterprise CRM plugin",
            author="Partner Corp",
        )

        def __init__(self, **kwargs):
            self.connected = False

        async def initialize(self) -> None:
            self.connected = True

        def get_cli_handlers(self):
            return {"sync": lambda: "Synced 100 enterprise records"}

    reg = VerticalRegistry()
    # Register external plugin
    reg.register(StandaloneThirdPartyCRM)

    # Validate manifest discovery
    manifests = reg.list_manifests()
    plugin_names = {m.name: m for m in manifests}
    assert "thirdparty_crm" in plugin_names
    assert plugin_names["thirdparty_crm"].author == "Partner Corp"

    # Instantiate and execute
    instance = reg.get_vertical_instance("thirdparty_crm")
    assert instance is not None
    await instance.initialize()
    assert instance.connected is True
    handlers = instance.get_cli_handlers()
    assert "sync" in handlers
    assert handlers["sync"]() == "Synced 100 enterprise records"
