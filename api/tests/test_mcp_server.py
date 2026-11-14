import asyncio
import importlib.util
import json
from pathlib import Path

import pytest
from mcp import Client
from mcp.server.mcpserver.exceptions import ToolError

from app import store
from app.models import AuditRequest, ProgressEvent

SERVER = Path(__file__).resolve().parents[2] / "mcp" / "server.py"


def _load():
    spec = importlib.util.spec_from_file_location("proveryai_mcp_server", SERVER)
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


DEMO = {
    "repo_url": "https://github.com/AlexAlexBabarika/Eurasian-Hack-14-Nov/tree/main/demo/fixture-app",
    "site_url": "http://localhost:4100/public/index.html",
    "policy_url": "http://localhost:4100/privacy.html",
}


def _text(result) -> str:
    return result.content[0].text


def _no_live_audit(module, monkeypatch, requests: list[AuditRequest] | None = None) -> list[str]:
    """Replace the pipeline with a stub that records the repo URLs (and requests) it was asked to audit."""
    calls: list[str] = []

    async def fake_run_audit(audit_id, req, emit, use_llm=True):
        calls.append(req.repo_url)
        if requests is not None:
            requests.append(req)
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


def _matrix_rows(text: str) -> list[str]:
    return [line.split("**")[1] for line in text.splitlines() if line.startswith("| **")]


def test_jurisdictions_is_an_optional_list_of_the_three_codes() -> None:
    schema = asyncio.run(_load().server.list_tools())[0].input_schema
    assert "jurisdictions" not in schema["required"]
    assert '"enum": ["UK", "EU", "KZ"]' in json.dumps(schema)


def test_live_audit_gets_the_selected_jurisdictions_in_matrix_order(monkeypatch) -> None:
    module = _load()
    requests: list[AuditRequest] = []
    _no_live_audit(module, monkeypatch, requests)
    monkeypatch.setenv("DEMO_MODE", "live")
    asyncio.run(module.server.call_tool("audit_product", {**DEMO, "jurisdictions": ["KZ", "UK", "KZ"]}))
    asyncio.run(module.server.call_tool("audit_product", DEMO))
    asyncio.run(module.server.call_tool("audit_product", {**DEMO, "jurisdictions": []}))
    assert [r.jurisdictions for r in requests] == [["UK", "KZ"], None, None]


def test_cached_report_shows_only_the_selected_jurisdictions(monkeypatch) -> None:
    module = _load()
    _no_live_audit(module, monkeypatch)
    monkeypatch.setenv("DEMO_MODE", "cached")
    text = _text(asyncio.run(module.server.call_tool("audit_product", {**DEMO, "jurisdictions": ["EU"]})))
    assert _matrix_rows(text) == ["EU"]
    assert "### EU / " in text
    assert "### UK / " not in text and "### KZ / " not in text
    everything = _text(asyncio.run(module.server.call_tool("audit_product", DEMO)))
    assert _matrix_rows(everything) == ["UK", "EU", "KZ"]


def test_unknown_jurisdiction_is_rejected(monkeypatch) -> None:
    module = _load()
    calls = _no_live_audit(module, monkeypatch)
    with pytest.raises(ToolError):
        asyncio.run(module.server.call_tool("audit_product", {**DEMO, "jurisdictions": ["US"]}))
    assert calls == []


@pytest.mark.parametrize(
    ("config", "root_placeholder"),
    [(".mcp.json", "${CLAUDE_PROJECT_DIR:-.}"), (".cursor/mcp.json", "${workspaceFolder}")],
)
def test_shipped_client_config_starts_this_server(config: str, root_placeholder: str) -> None:
    root = SERVER.parents[1]
    entry = json.loads((root / config).read_text())["mcpServers"]["proveryai"]
    args = [a.replace(root_placeholder, str(root)) for a in entry["args"]]
    assert entry["command"] == "uv"
    assert args == ["run", "--project", str(root / "api"), "python", str(SERVER)]


def _call_with_progress(module, arguments: dict) -> tuple[str, list[tuple[float, float | None, str | None]]]:
    """Call the tool the way an assistant does, over an MCP session, and collect its progress notifications."""
    seen: list[tuple[float, float | None, str | None]] = []

    async def on_progress(progress: float, total: float | None, message: str | None) -> None:
        seen.append((progress, total, message))

    async def call() -> str:
        async with Client(module.server) as client:
            return _text(await client.call_tool("audit_product", arguments, progress_callback=on_progress))

    return asyncio.run(call()), seen


def test_live_audit_reports_each_pipeline_event_as_progress(monkeypatch) -> None:
    module = _load()

    async def fake_run_audit(audit_id, req, emit, use_llm=True):
        emit(ProgressEvent(step="clone", status="running", message="Fetching repository"))
        emit(ProgressEvent(step="clone", status="error", message="Could not fetch repository: boom"))
        emit(ProgressEvent(step="done", status="done", message="Audit finished in 1s"))
        return store.find_cached(AuditRequest(**DEMO)).report

    monkeypatch.setattr(module, "run_audit", fake_run_audit)
    monkeypatch.setenv("DEMO_MODE", "live")
    text, seen = _call_with_progress(module, DEMO)
    assert text.startswith("# Proveryai audit")
    assert seen == [
        (1, 19, "Fetching repository"),
        (2, 19, "Could not fetch repository: boom"),
        (19, 19, "Audit finished in 1s"),
    ]


def test_saved_report_is_returned_without_progress(monkeypatch) -> None:
    module = _load()
    _no_live_audit(module, monkeypatch)
    monkeypatch.setenv("DEMO_MODE", "cached")
    text, seen = _call_with_progress(module, DEMO)
    assert text.startswith("# Proveryai audit")
    assert seen == []
