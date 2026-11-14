"""A step that raises emits status=error and the audit still returns a report and a final done event."""

import asyncio
from unittest.mock import patch

import pytest

from app import pipeline, sample
from app.ingest.site import SiteScan
from app.models import AuditReport, AuditRequest, ProgressEvent

REQ = AuditRequest(repo_url=str(sample.FIXTURE), site_url=sample.SITE_URL, policy_url=str(sample.FIXTURE / "privacy.html"))


def audit(use_llm: bool = False) -> tuple[AuditReport, list[ProgressEvent]]:
    events: list[ProgressEvent] = []

    async def fake_scan(url: str) -> SiteScan:
        return sample.FIXTURE_SCAN

    with patch("app.ingest.site.scan", fake_scan):
        report = asyncio.run(pipeline.run_audit("t", REQ, events.append, use_llm=use_llm))
    return report, events


def last(events: list[ProgressEvent], step: str) -> ProgressEvent:
    return [e for e in events if e.step == step][-1]


def boom(*args: object, **kwargs: object) -> None:
    raise RuntimeError("boom")


def test_rule_engine_failure_emits_diff_error_and_the_audit_finishes(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(pipeline, "run_rules", boom)
    report, events = audit()
    assert report.findings == []
    assert last(events, "diff").status == "error" and "boom" in last(events, "diff").message
    assert not [e for e in events if e.step == "diff" and e.status == "done"]
    assert last(events, "verdict").status == "done" and report.matrix
    assert events[-1].step == "done" and events[-1].status == "done"


def test_claims_failure_emits_claims_error_and_the_audit_finishes(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(pipeline.claims_extract, "heuristic", boom)
    report, events = audit()
    assert report.claims == pipeline.EMPTY_CLAIMS
    assert last(events, "claims").status == "error"
    assert last(events, "diff").status == "done"
    assert events[-1].step == "done"


def test_verdict_failure_emits_law_and_verdict_errors_and_returns_an_empty_matrix(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(pipeline, "build_matrix", boom)
    report, events = audit()
    assert report.matrix == [] and report.provisions == {}
    assert report.findings
    assert last(events, "law").status == last(events, "verdict").status == "error"
    assert report.stats["verdict_method"] == "error"
    assert AuditReport.model_validate(report.model_dump()) == report
    assert events[-1].step == "done" and events[-1].status == "done"


def test_verdict_failure_with_llm_retries_without_it(monkeypatch: pytest.MonkeyPatch):
    real = pipeline.build_matrix
    calls: list[bool] = []

    async def flaky(*args: object, use_llm: bool = True, **kwargs: object):  # noqa: ANN202
        calls.append(use_llm)
        if use_llm:
            raise RuntimeError("boom")
        return await real(*args, use_llm=False, **kwargs)

    monkeypatch.setattr(pipeline, "build_matrix", flaky)
    monkeypatch.setattr(pipeline.claims_extract.llm, "available", lambda: False)
    report, events = audit(use_llm=True)
    assert calls == [True, False]
    assert report.matrix and report.provisions
    assert report.stats["verdict_method"] == "deterministic"
    assert last(events, "law").status == "done"
    verdict = last(events, "verdict")
    assert verdict.status == "error" and "template text" in verdict.message and "boom" in verdict.message
    assert events[-1].step == "done" and events[-1].status == "done"
