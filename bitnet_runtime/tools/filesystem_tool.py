from __future__ import annotations
import os
from pathlib import Path
from typing import Any, List, Optional
from .base import BaseTool, ToolResult

class FilesystemBaseTool(BaseTool):
    def __init__(self, base_dir: Path | str = "./workspace"):
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_safe_path(self, target_path: str) -> Path:
        resolved = (self.base_dir / target_path).resolve()
        # Ensure path is within base_dir (or allow relative navigation if within base)
        try:
            resolved.relative_to(self.base_dir)
            return resolved
        except ValueError:
            # Fallback: keep constrained to base_dir
            return self.base_dir / Path(target_path).name

class ReadFileTool(FilesystemBaseTool):
    name = "read_file"
    description = "Reads text content from a specified file inside the workspace."
    parameters_schema = {
        "type": "object",
        "properties": {"file_path": {"type": "string", "description": "Relative path to file"}},
        "required": ["file_path"],
    }

    async def execute(self, file_path: str, **kwargs: Any) -> ToolResult:
        try:
            target = self._resolve_safe_path(file_path)
            if not target.exists():
                return ToolResult(success=False, output="", error=f"File does not exist: {file_path}")
            content = target.read_text(encoding="utf-8", errors="replace")
            return ToolResult(success=True, output=content)
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

class WriteFileTool(FilesystemBaseTool):
    name = "write_file"
    description = "Writes text content to a file inside the workspace."
    parameters_schema = {
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Relative path to file"},
            "content": {"type": "string", "description": "Text content to write"},
        },
        "required": ["file_path", "content"],
    }

    async def execute(self, file_path: str, content: str, **kwargs: Any) -> ToolResult:
        try:
            target = self._resolve_safe_path(file_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return ToolResult(success=True, output=f"Successfully wrote {len(content)} characters to {file_path}")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

class ListDirectoryTool(FilesystemBaseTool):
    name = "list_directory"
    description = "Lists files and subdirectories in the specified workspace directory."
    parameters_schema = {
        "type": "object",
        "properties": {"dir_path": {"type": "string", "description": "Relative directory path (empty for root)"}},
        "required": [],
    }

    async def execute(self, dir_path: str = "", **kwargs: Any) -> ToolResult:
        try:
            target = self._resolve_safe_path(dir_path) if dir_path else self.base_dir
            if not target.exists():
                return ToolResult(success=False, output="", error=f"Directory does not exist: {dir_path}")

            items = []
            for entry in target.iterdir():
                kind = "DIR" if entry.is_dir() else "FILE"
                size = entry.stat().st_size if entry.is_file() else "-"
                items.append(f"[{kind}] {entry.name} ({size} bytes)")

            output = "\n".join(items) if items else "(Empty directory)"
            return ToolResult(success=True, output=output)
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

class SearchFilesTool(FilesystemBaseTool):
    name = "search_files"
    description = "Searches for files matching a glob pattern in the workspace."
    parameters_schema = {
        "type": "object",
        "properties": {"pattern": {"type": "string", "description": "Glob pattern, e.g. *.txt or **/*.py"}},
        "required": ["pattern"],
    }

    async def execute(self, pattern: str, **kwargs: Any) -> ToolResult:
        try:
            matches = [str(p.relative_to(self.base_dir)) for p in self.base_dir.glob(pattern)]
            output = "\n".join(matches) if matches else "No files matched."
            return ToolResult(success=True, output=output)
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

def get_filesystem_tools(base_dir: Path | str = "./workspace") -> List[BaseTool]:
    return [
        ReadFileTool(base_dir),
        WriteFileTool(base_dir),
        ListDirectoryTool(base_dir),
        SearchFilesTool(base_dir),
    ]
