import asyncio
import importlib.util
from pathlib import Path

import pytest
from mcp.server.mcpserver.exceptions import ToolError

SERVER = Path(__file__).resolve().parents[2] / "mcp" / "server.py"


def _load():
    spec = importlib.util.spec_from_file_location("groundtruth_mcp_server", SERVER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_tool_is_registered() -> None:
    tools = asyncio.run(_load().server.list_tools())
    assert [t.name for t in tools] == ["audit_product"]


def test_bad_url_reaches_the_client_with_its_message() -> None:
    with pytest.raises(ToolError, match=r"repo_url must be an http\(s\) URL"):
        asyncio.run(
            _load().server.call_tool(
                "audit_product", {"repo_url": "not-a-url", "site_url": "http://x", "policy_url": "http://x"}
            )
        )


def test_repo_and_site_are_optional_but_not_both_missing() -> None:
    server = _load().server
    tool = asyncio.run(server.list_tools())[0]
    assert tool.input_schema["required"] == ["policy_url"]
    with pytest.raises(ToolError, match="give a repo_url, a site_url, or both"):
        asyncio.run(server.call_tool("audit_product", {"policy_url": "http://x"}))
    with pytest.raises(ToolError, match=r"site_url must be an http\(s\) URL"):
        asyncio.run(server.call_tool("audit_product", {"site_url": "ftp://x", "policy_url": "http://x"}))
