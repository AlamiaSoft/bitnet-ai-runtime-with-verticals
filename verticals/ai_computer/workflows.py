from __future__ import annotations
import os
from pathlib import Path
from typing import Any, Dict, List
from bitnet_runtime.tools.shell_tool import RunShellTool

class ProjectInspector:
    def __init__(self, project_path: Path | str = "."):
        self.project_path = Path(project_path).resolve()

    def inspect_structure(self) -> Dict[str, Any]:
        has_git = (self.project_path / ".git").exists()
        has_pyproject = (self.project_path / "pyproject.toml").exists()
        has_package_json = (self.project_path / "package.json").exists()
        has_dockerfile = (self.project_path / "Dockerfile").exists()

        file_count = sum(1 for _ in self.project_path.glob("**/*") if _.is_file())

        return {
            "path": str(self.project_path),
            "is_git_repo": has_git,
            "type": "python" if has_pyproject else ("nodejs" if has_package_json else "generic"),
            "has_docker": has_dockerfile,
            "total_files": file_count,
        }

class BuildRunner:
    def __init__(self, working_dir: Path | str = "."):
        self.shell = RunShellTool(working_dir)

    async def run_lint_or_tests(self, command: str) -> Dict[str, Any]:
        res = await self.shell.execute(command)
        return {
            "command": command,
            "success": res.success,
            "output": res.output,
            "error": res.error,
        }
