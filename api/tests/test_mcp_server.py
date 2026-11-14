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
