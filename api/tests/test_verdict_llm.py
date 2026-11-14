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

    def run(verdict: Handler, effort: str = "fast") -> tuple[AuditReport, list[ProgressEvent], list[dict]]:
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
                           policy_url=str(sample.FIXTURE / "privacy.html"), effort=effort)  # fmt: skip
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


def test_effort_picks_the_model(llm_audit, monkeypatch):
    monkeypatch.setenv("MODEL_STRONG", "vendor/strong")
    report, _, bodies = llm_audit(lambda body: tool_reply(prose()))
    assert {b["model"] for b in bodies} == {"vendor/model"} and report.stats["effort"] == "fast"
    report, _, bodies = llm_audit(lambda body: tool_reply(prose()), effort="strong")
    assert {b["model"] for b in bodies} == {"vendor/strong"} and report.stats["effort"] == "strong"


def test_verdict_calls_skip_reasoning_and_cap_output(llm_audit, monkeypatch):
    monkeypatch.setenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
    _, _, bodies = llm_audit(lambda body: tool_reply(prose()))
    assert all(b["reasoning"] == {"enabled": False} and b["max_tokens"] <= 1500 for b in bodies)


BAD_HEADLINES = [
    "Policy says it never shares data, yet Sentry, Mixpanel, OpenAI, PostHog, Stripe and Google Analytics receive it",
    "Mixpanel receives device_id and user_content",
    "Six vendors receive personal data the policy says is never shared",
    "Possible inconsistency with EU-GDPR-13-1-e: Mixpanel is not named",
]


@pytest.mark.parametrize("bad", BAD_HEADLINES)
def test_a_headline_that_breaks_the_rules_is_sent_back_once_with_the_reason(llm_audit, bad):
    def verdict(body: dict) -> httpx.Response:
        retry = "failed validation" in body["messages"][1]["content"]
        return tool_reply(prose("6 vendors receive personal data; policy says none is shared" if retry else bad))

    report, _, bodies = llm_audit(verdict)
    assert len(bodies) == 18
    written = [c.headline for c in report.matrix if c.finding_ids]
    assert set(written) == {"6 vendors receive personal data; policy says none is shared"}


def test_headlines_obey_the_rules_even_when_the_model_never_does(llm_audit):
    report, _, _ = llm_audit(lambda body: tool_reply(prose(BAD_HEADLINES[0] + " (device_id, ip)")))
    for cell in report.matrix:
        assert len(cell.headline) <= 90, cell.headline
        assert "_" not in cell.headline, cell.headline


def test_verdict_prompt_gives_human_labels_and_the_headline_rules(llm_audit):
    _, _, bodies = llm_audit(lambda body: tool_reply(prose()))
    system, user = bodies[0]["messages"][0]["content"], "\n".join(b["messages"][1]["content"] for b in bodies)
    assert "90 characters" in system and "digits" in system
    for raw in ["device_id", "user_content", "error_monitoring", "ai_processing", "['"]:
        assert raw not in user, raw
    assert "device ID" in user and "IP address" in user and "user content" in user


def test_cells_that_fall_back_to_template_text_are_counted(llm_audit):
    def verdict(body: dict) -> httpx.Response:
        user = body["messages"][1]["content"]
        if "Jurisdiction: KZ" in user:
            return httpx.Response(500)  # the call fails twice
        if "Jurisdiction: UK" in user and "AI transparency" in user:
            return tool_reply(prose("This is illegal"))  # prose rejected for banned wording
        return tool_reply(prose())

    report, events, _ = llm_audit(verdict)
    assert report.stats["verdict_fallbacks"] == 4
    done = next(e for e in events if e.step == "verdict" and e.status == "done")
    assert "4 of 9" in done.message and "template" in done.message

    clean, events, _ = llm_audit(lambda body: tool_reply(prose()))
    assert clean.stats["verdict_fallbacks"] == 0
    assert "template" not in next(e for e in events if e.step == "verdict" and e.status == "done").message
