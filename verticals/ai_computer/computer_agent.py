from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, Optional
from bitnet_runtime.logging import logger
from bitnet_runtime.agent.agent import Agent, AgentRunResult
from bitnet_runtime.tools.filesystem_tool import get_filesystem_tools
from bitnet_runtime.tools.shell_tool import RunShellTool
from bitnet_runtime.plugins.vertical_registry import VerticalManifest
from ..base_vertical import BaseVertical
from .workflows import BuildRunner, ProjectInspector

class AIComputerAgent(BaseVertical):
    manifest = VerticalManifest(
        name="computer",
        title="AI Computer Operator",
        description="Desktop & Repository Automation Operator",
    )
    """
    Autonomous Desktop and Project Operator:
    - Inspects project structures and dependencies
    - Runs linting, tests, and builds
    - Performs file organization and repository maintenance
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.inspector = ProjectInspector(self.config.agent.working_dir)
        self.build_runner = BuildRunner(self.config.agent.working_dir)
        self._init_agent()

    def _init_agent(self) -> None:
        self.tool_registry.register_many(get_filesystem_tools(self.config.agent.working_dir))
        self.tool_registry.register(RunShellTool(self.config.agent.working_dir))
        self.agent = Agent(
            name="AIComputerOperator",
            inference_engine=self.inference_engine,
            tool_registry=self.tool_registry,
            episodic_memory=self.episodic_memory,
            semantic_memory=self.semantic_memory,
        )

    async def initialize(self) -> None:
        logger.info("AI Computer Operator initialized.")

    async def execute_task(self, prompt: str) -> AgentRunResult:
        return await self.agent.run(prompt)

    async def inspect_and_audit(self, target_dir: Optional[str] = None) -> Dict[str, Any]:
        inspector = ProjectInspector(target_dir or self.config.agent.working_dir)
        structure = inspector.inspect_structure()
        prompt = f"""Analyze this repository structure and give recommendations for optimization and test readiness:
Project Info: {structure}
"""
        resp = await self.inference_engine.complete(prompt)
        return {
            "structure": structure,
            "recommendations": resp.text,
        }
