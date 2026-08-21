from __future__ import annotations
import asyncio
import os
import shlex
from pathlib import Path
from typing import Any, List, Optional
from ..policy.policy_engine import PolicyDecision, SecurityPolicyEngine
from .base import BaseTool, ToolResult

class RunShellTool(BaseTool):
    name = "run_shell"
    description = "Executes a shell command locally with deterministic security policy constraints and timeout."
    parameters_schema = {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Shell command to run"},
            "timeout_seconds": {"type": "integer", "description": "Execution timeout limit", "default": 30},
        },
        "required": ["command"],
    }

    def __init__(
        self,
        working_dir: Path | str = "./workspace",
        policy_engine: Optional[SecurityPolicyEngine] = None,
    ):
        self.working_dir = Path(working_dir).resolve()
        self.working_dir.mkdir(parents=True, exist_ok=True)
        self.policy_engine = policy_engine or SecurityPolicyEngine()

    async def execute(self, command: str, timeout_seconds: int = 30, **kwargs: Any) -> ToolResult:
        # Evaluate security policy
        eval_result = self.policy_engine.evaluate_shell_command(command, self.working_dir)
        if eval_result.decision != PolicyDecision.ALLOW:
            return ToolResult(
                success=False,
                output="",
                error=f"Security Policy Violation: {eval_result.reason}",
            )

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                cwd=str(self.working_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=float(timeout_seconds))
            except asyncio.TimeoutError:
                proc.kill()
                return ToolResult(success=False, output="", error=f"Command timed out after {timeout_seconds} seconds.")

            out_str = stdout.decode("utf-8", errors="replace").strip()
            err_str = stderr.decode("utf-8", errors="replace").strip()

            combined = out_str
            if err_str:
                combined += f"\nSTDERR:\n{err_str}"

            # Truncate very long output
            if len(combined) > 4000:
                combined = combined[:4000] + "\n...[Output Truncated]..."

            return ToolResult(
                success=(proc.returncode == 0),
                output=combined or "(No output)",
                error=err_str if proc.returncode != 0 else None,
                data={"exit_code": proc.returncode},
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
