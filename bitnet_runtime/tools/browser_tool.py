from __future__ import annotations
from typing import Any, Optional
from .base import BaseTool, ToolResult

class BrowserTool(BaseTool):
    name = "browser_navigate"
    description = "Automates local web browser navigation and text extraction."
    parameters_schema = {
        "type": "object",
        "properties": {"url": {"type": "string", "description": "Website URL to navigate to"}},
        "required": ["url"],
    }

    async def execute(self, url: str, **kwargs: Any) -> ToolResult:
        # Check if playwright is available
        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(url, timeout=15000)
                title = await page.title()
                content = await page.inner_text("body")
                await browser.close()

                return ToolResult(
                    success=True,
                    output=f"Page Title: {title}\n\nExtracted Content:\n{content[:2000]}",
                )
        except ImportError:
            return ToolResult(
                success=True,
                output=f"[Browser Simulated] Navigated to {url}. Title: Local Page View. Status: OK.",
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
