from __future__ import annotations
import httpx
from typing import Any, Dict, Optional
from .base import BaseTool, ToolResult

class HttpGetTool(BaseTool):
    name = "http_get"
    description = "Sends an HTTP GET request to a local or external URL."
    parameters_schema = {
        "type": "object",
        "properties": {"url": {"type": "string", "description": "Target URL"}},
        "required": ["url"],
    }

    async def execute(self, url: str, **kwargs: Any) -> ToolResult:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.get(url)
                return ToolResult(
                    success=(res.status_code < 400),
                    output=res.text[:3000],
                    data={"status_code": res.status_code},
                )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

class HttpPostTool(BaseTool):
    name = "http_post"
    description = "Sends an HTTP POST request with JSON payload."
    parameters_schema = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Target URL"},
            "json_data": {"type": "object", "description": "JSON body"},
        },
        "required": ["url", "json_data"],
    }

    async def execute(self, url: str, json_data: Dict[str, Any], **kwargs: Any) -> ToolResult:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(url, json=json_data)
                return ToolResult(
                    success=(res.status_code < 400),
                    output=res.text[:3000],
                    data={"status_code": res.status_code},
                )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
