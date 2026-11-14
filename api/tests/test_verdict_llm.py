"""The verdict step with a mocked OpenAI-compatible endpoint: progress events, prose rules, fallbacks. No network."""

import asyncio
import json
from collections.abc import Callable
from unittest.mock import patch

import httpx
import pytest

from app import llm, sample
from app.ingest.site import SiteScan
from app.models import AuditReport, AuditRequest, ProgressEvent
from app.pipeline import run_audit

Handler = Callable[[dict], httpx.Response]


def tool_reply(arguments: dict) -> httpx.Response:
    call = {"id": "1", "type": "function", "function": {"name": "submit", "arguments": json.dumps(arguments)}}
    return httpx.Response(200, json={"choices": [{"message": {"role": "assistant", "tool_calls": [call]}}]})


def prose(headline: str = "Mixpanel receives email addresses the policy does not mention") -> dict:
    return {"headline": headline, "reasoning": "Possible inconsistency with the cited provisions.",
            "provision_ids": [], "fixes": []}  # fmt: skip


@pytest.fixture
def llm_audit(monkeypatch, tmp_path):
    """Runs the fixture audit with an LLM key set; `verdict` answers each verdict call (claims calls get a 500)."""
    monkeypatch.setattr(llm, "CACHE_DIR", tmp_path)
    monkeypatch.setenv("LLM_API_KEY", "sk-test")
    monkeypatch.setenv("LLM_BASE_URL", "https://llm.test/v1")
    monkeypatch.setenv("MODEL_FAST", "vendor/model")

    def run(verdict: Handler) -> tuple[AuditReport, list[ProgressEvent], list[dict]]:
        bodies: list[dict] = []

        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            if "CellProse" not in body["tools"][0]["function"]["description"]:
                return httpx.Response(500)
            bodies.append(body)
            return verdict(body)

        async def fake_scan(url: str) -> SiteScan:
            return sample.FIXTURE_SCAN

        monkeypatch.setattr(llm, "_transport", httpx.MockTransport(handler))
        events: list[ProgressEvent] = []
        req = AuditRequest(repo_url=str(sample.FIXTURE), site_url=sample.SITE_URL,
                           policy_url=str(sample.FIXTURE / "privacy.html"))  # fmt: skip
        with patch("app.ingest.site.scan", fake_scan):
            report = asyncio.run(run_audit("t", req, events.append))
        return report, events, bodies

    return run


def test_each_finished_cell_emits_a_verdict_progress_event(llm_audit):
    report, events, bodies = llm_audit(lambda body: tool_reply(prose()))
    assert len(bodies) == 9  # 3 jurisdictions x 3 areas; financial cells need no LLM
    verdict = [e for e in events if e.step == "verdict"]
    assert [e.status for e in verdict] == ["running"] * 13 + ["done"]
    assert [e.count for e in verdict[1:13]] == list(range(1, 13))
    assert "12 of 12" in verdict[12].message
    assert verdict[-1].count == len(report.matrix) == 12


def test_verdict_calls_skip_reasoning_and_cap_output(llm_audit, monkeypatch):
    monkeypatch.setenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
    _, _, bodies = llm_audit(lambda body: tool_reply(prose()))
    assert all(b["reasoning"] == {"enabled": False} and b["max_tokens"] <= 1500 for b in bodies)
