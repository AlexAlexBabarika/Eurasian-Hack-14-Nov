"""Input modes (repo only, site only), the fixed-policy fixture, the CLI gate and the examples list."""

import asyncio
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app import cli, sample, store
from app.ingest.site import SiteScan
from app.main import app
from app.models import AuditReport, AuditRequest, ProgressEvent
from app.pipeline import run_audit
from app.report.markdown import finding_status_by_jurisdiction

POLICY = str(sample.FIXTURE / "privacy.html")


def audit(req: AuditRequest) -> tuple[AuditReport, dict[str, str]]:
    events: list[ProgressEvent] = []

    async def fake_scan(url: str) -> SiteScan:
        return sample.FIXTURE_SCAN

    with patch("app.ingest.site.scan", fake_scan):
        report = asyncio.run(run_audit("t", req, events.append, use_llm=False))
    return report, {e.step: e.status for e in events}


def rules(report: AuditReport) -> set[str]:
    return {f.rule.split("_")[0] for f in report.findings}


def statuses(report: AuditReport, area: str) -> dict[str, str]:
    return {c.jurisdiction: c.status for c in report.matrix if c.area == area}


def test_request_needs_a_repo_or_a_site():
    with pytest.raises(ValidationError):
        AuditRequest(policy_url="https://x.test/privacy")
    assert AuditRequest(repo_url="https://github.com/a/b", policy_url="https://x.test/privacy").site_url is None
    assert AuditRequest(site_url="https://x.test", policy_url="https://x.test/privacy").repo_url is None


def test_site_only_audit_skips_the_code_steps():
    report, steps = audit(AuditRequest(site_url=sample.SITE_URL, policy_url=POLICY))
    assert steps["clone"] == steps["manifests"] == "skipped"
    assert steps["site_scan"] == "done"
    assert "R5" in rules(report)
    assert not {"R7", "R8"} & rules(report)
    assert all(f.evidence for f in report.findings)
    ai = [c for c in report.matrix if c.area == "ai_transparency"]
    assert ai and all(c.status == "grey" and "no repository was given" in c.headline for c in ai)


def test_repo_only_audit_skips_the_site_scan():
    report, steps = audit(AuditRequest(repo_url=str(sample.FIXTURE), policy_url=POLICY))
    assert steps["site_scan"] == "skipped"
    assert steps["clone"] == "done"
    assert "R5" not in rules(report)
    assert report.findings and all(f.evidence for f in report.findings)


def test_a_cell_without_findings_is_grey_when_no_site_was_loaded():
    fixed = str(sample.FIXTURE / sample.FIXED_POLICY)
    report, _ = audit(AuditRequest(repo_url=str(sample.FIXTURE), policy_url=fixed))
    ai = [c for c in report.matrix if c.area == "ai_transparency"]
    assert all(c.status == "grey" and c.headline == "Not assessed: no live site was given" for c in ai)
    assert set(statuses(report, "personal_data").values()) == {"amber"}


def test_fixed_policy_leaves_only_the_findings_that_need_code_changes():
    report = asyncio.run(sample.build("t", sample.FIXED_POLICY)).report
    assert rules(report) == {"R5", "R8"}
    personal = statuses(report, "personal_data")
    assert (personal["UK"], personal["EU"]) == ("amber", "red")
    assert set(statuses(report, "ai_transparency").values()) == {"green"}


def test_cli_exit_codes_and_markdown(tmp_path, capsys):
    base = ["--repo", str(sample.FIXTURE), "--policy", POLICY, "--no-llm"]
    out = tmp_path / "report.md"
    assert cli.main([*base, "--fail-on", "red", "--markdown", str(out)]) == cli.EXIT_FAILED_GATE
    assert out.read_text().startswith("# Groundtruth audit report")
    assert "RED" in capsys.readouterr().out
    assert cli.main([*base, "--fail-on", "never"]) == 0
    fixed = ["--repo", str(sample.FIXTURE), "--policy", str(sample.FIXTURE / sample.FIXED_POLICY), "--no-llm"]
    assert cli.main([*fixed, "--fail-on", "red"]) == 0
    assert cli.main([*fixed, "--fail-on", "amber"]) == cli.EXIT_FAILED_GATE


def test_cli_reports_an_unreadable_repo_as_incomplete(tmp_path):
    missing = str(tmp_path / "missing")
    assert cli.main(["--repo", missing, "--policy", POLICY, "--no-llm", "--fail-on", "never"]) == cli.EXIT_INCOMPLETE


def test_summaries_list_the_demo_fixture():
    by_id = {s.id: s for s in store.summaries()}
    assert "demo-fixture" in by_id
    assert sum(by_id["demo-fixture"].status_counts.values()) == 12


def test_finding_status_by_jurisdiction(report):
    r5 = next(f for f in report.findings if f.rule.startswith("R5"))
    by_jurisdiction = finding_status_by_jurisdiction(report, r5.id)
    assert (by_jurisdiction["UK"], by_jurisdiction["EU"]) == ("amber", "red")


def test_examples_route_and_request_validation():
    client = TestClient(app)
    listed = client.get("/audits")
    assert listed.status_code == 200
    assert isinstance(listed.json(), list)
    assert client.post("/audits", json={"policy_url": "https://x.test/privacy"}).status_code == 422
