from __future__ import annotations
from typing import Dict, List, Optional
from .base import BaseTool, ToolResult

class ToolRegistry:
    """Central registry for discovering and executing agent tools."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def register_many(self, tools: List[BaseTool]) -> None:
        for t in tools:
            self.register(t)

    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def list_tools(self) -> List[BaseTool]:
        return list(self._tools.values())

    def get_tools_description(self) -> str:
        lines = []
        for t in self._tools.values():
            lines.append(f"- **{t.name}**: {t.description}")
            params = t.parameters_schema.get("properties", {})
            req = t.parameters_schema.get("required", [])
            param_list = [f"{k}{' (required)' if k in req else ''}" for k in params.keys()]
            if param_list:
                lines.append(f"  Parameters: {', '.join(param_list)}")
        return "\n".join(lines)

    async def execute_tool(self, tool_name: str, **kwargs) -> ToolResult:
        tool_obj = self.get_tool(tool_name)
        if not tool_obj:
            return ToolResult(success=False, output="", error=f"Tool '{tool_name}' not found.")
        return await tool_obj.execute(**kwargs)
