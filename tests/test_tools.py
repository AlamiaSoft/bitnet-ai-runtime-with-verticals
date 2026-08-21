import pytest
from pathlib import Path
from bitnet_runtime.tools.base import BaseTool, ToolResult, tool
from bitnet_runtime.tools.filesystem_tool import (
    ListDirectoryTool,
    ReadFileTool,
    SearchFilesTool,
    WriteFileTool,
)
from bitnet_runtime.tools.http_tool import HttpGetTool
from bitnet_runtime.tools.registry import ToolRegistry
from bitnet_runtime.tools.shell_tool import RunShellTool

@pytest.fixture
def workspace(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    return ws

@pytest.mark.asyncio
async def test_filesystem_tools(workspace):
    write_tool = WriteFileTool(workspace)
    read_tool = ReadFileTool(workspace)
    list_tool = ListDirectoryTool(workspace)
    search_tool = SearchFilesTool(workspace)

    # Write
    w_res = await write_tool.execute(file_path="sub/test.txt", content="Hello Workspace")
    assert w_res.success is True

    # Read
    r_res = await read_tool.execute(file_path="sub/test.txt")
    assert r_res.success is True
    assert r_res.output == "Hello Workspace"

    # List
    l_res = await list_tool.execute(dir_path="")
    assert l_res.success is True
    assert "sub" in l_res.output

    # Search
    s_res = await search_tool.execute(pattern="**/*.txt")
    assert s_res.success is True
    assert "test.txt" in s_res.output

@pytest.mark.asyncio
async def test_shell_tool_safety(workspace):
    shell_tool = RunShellTool(workspace)

    # Allowed safe command
    res = await shell_tool.execute(command='python -c "print(\'SHELL_OK\')\"')
    assert res.success is True
    assert "SHELL_OK" in res.output

    # Blocked dangerous command
    bad_res = await shell_tool.execute(command="rm -rf /")
    assert bad_res.success is False
    assert "policy violation" in bad_res.error.lower() or "critical" in bad_res.error.lower() or "blocked" in bad_res.error.lower()

@pytest.mark.asyncio
async def test_custom_decorated_tool():
    @tool(name="add_numbers", description="Adds two numbers together")
    def add_numbers(a: int, b: int) -> int:
        return a + b

    registry = ToolRegistry()
    registry.register(add_numbers)

    assert registry.get_tool("add_numbers") is not None
    res = await registry.execute_tool("add_numbers", a=10, b=25)
    assert res.success is True
    assert res.output == "35"
