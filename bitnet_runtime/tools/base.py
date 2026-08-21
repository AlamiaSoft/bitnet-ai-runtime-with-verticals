from __future__ import annotations
import inspect
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Type
from pydantic import BaseModel

@dataclass
class ToolResult:
    success: bool
    output: str
    error: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

    def to_string(self) -> str:
        if self.success:
            return self.output
        return f"Error: {self.error or self.output}"

class BaseTool(ABC):
    """Abstract interface for all executable agent tools."""

    name: str
    description: str
    parameters_schema: Dict[str, Any]

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        pass

def tool(name: Optional[str] = None, description: Optional[str] = None):
    """Decorator to convert a Python function into an agent tool."""
    def decorator(func: Callable) -> BaseTool:
        tool_name = name or func.__name__
        tool_desc = description or (func.__doc__ or "").strip()

        sig = inspect.signature(func)
        properties = {}
        required = []

        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls"):
                continue
            param_type = "string"
            if param.annotation == int:
                param_type = "integer"
            elif param.annotation == float:
                param_type = "number"
            elif param.annotation == bool:
                param_type = "boolean"
            elif param.annotation == dict:
                param_type = "object"
            elif param.annotation == list:
                param_type = "array"

            properties[param_name] = {"type": param_type}
            if param.default == inspect.Parameter.empty:
                required.append(param_name)

        class FunctionalTool(BaseTool):
            name = tool_name
            description = tool_desc
            parameters_schema = {
                "type": "object",
                "properties": properties,
                "required": required,
            }

            async def execute(self, **kwargs: Any) -> ToolResult:
                try:
                    if inspect.iscoroutinefunction(func):
                        res = await func(**kwargs)
                    else:
                        res = func(**kwargs)

                    if isinstance(res, ToolResult):
                        return res
                    return ToolResult(success=True, output=str(res))
                except Exception as e:
                    return ToolResult(success=False, output="", error=str(e))

        return FunctionalTool()

    return decorator
