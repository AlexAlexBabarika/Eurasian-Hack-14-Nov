import asyncio
import importlib.util
from pathlib import Path

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from app import store
from app.models import AuditRequest

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


DEMO = {
    "repo_url": "https://github.com/AlexAlexBabarika/Eurasian-Hack-14-Nov/tree/main/demo/fixture-app",
    "site_url": "http://localhost:4100/public/index.html",
    "policy_url": "http://localhost:4100/privacy.html",
}


def _text(result) -> str:
    return result.content[0].text


def _no_live_audit(module, monkeypatch) -> list[str]:
    """Replace the pipeline with a stub that records the repo URLs it was asked to audit."""
    calls: list[str] = []

    async def fake_run_audit(audit_id, req, emit, use_llm=True):
        calls.append(req.repo_url)
        return store.find_cached(AuditRequest(**DEMO)).report

    monkeypatch.setattr(module, "run_audit", fake_run_audit)
    return calls


def test_cached_mode_returns_the_saved_report_without_running_an_audit(monkeypatch) -> None:
    module = _load()
    calls = _no_live_audit(module, monkeypatch)
    monkeypatch.setenv("DEMO_MODE", "cached")
    text = _text(asyncio.run(module.server.call_tool("audit_product", DEMO)))
    assert calls == []
    assert "possible inconsistenc" in text.lower()


def test_cached_mode_runs_live_for_inputs_without_a_saved_audit(monkeypatch) -> None:
    module = _load()
    calls = _no_live_audit(module, monkeypatch)
    monkeypatch.setenv("DEMO_MODE", "cached")
    other = {**DEMO, "repo_url": "https://github.com/example/other"}
    asyncio.run(module.server.call_tool("audit_product", other))
    assert calls == ["https://github.com/example/other"]


def test_live_mode_ignores_saved_audits(monkeypatch) -> None:
    module = _load()
    calls = _no_live_audit(module, monkeypatch)
    monkeypatch.setenv("DEMO_MODE", "live")
    asyncio.run(module.server.call_tool("audit_product", DEMO))
    assert calls == [DEMO["repo_url"]]
