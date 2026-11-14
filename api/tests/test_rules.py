"""Golden tests on demo/fixture-app."""

import json
from pathlib import Path

from app.claims.extract import heuristic, validate_quotes
from app.detect.code_signals import CodeSignals
from app.diff.rules import run_rules
from app.models import AuditReport, Evidence, Observation

ROOT = Path(__file__).resolve().parents[2]


def by_vendor(report):
    return {o.vendor: o for o in report.observations}


def test_detects_planted_vendors_with_file_and_line(report):
    obs = by_vendor(report)
    for vendor in ["Mixpanel", "Sentry", "OpenAI", "Stripe", "PostHog"]:
        assert vendor in obs, f"{vendor} not detected"
        assert any(e.kind == "code" and e.file and e.line for e in obs[vendor].evidence), vendor
    assert {"email", "name"} <= set(obs["Mixpanel"].data_categories)
    assert "user_content" in obs["OpenAI"].data_categories and obs["OpenAI"].is_ai
    assert "next" not in {(o.vendor or "").lower() for o in report.observations}


def test_pre_consent_trackers(report):
    obs = by_vendor(report)
    assert obs["PostHog"].pre_consent and obs["Google Analytics"].pre_consent
    assert not obs["Mixpanel"].pre_consent and not obs["Stripe"].pre_consent


def test_claims_from_fixture_policy(report):
    c = report.claims
    assert c.sharing_statement == "no_sharing"
    assert not c.mentions_ai and not c.international_transfers and not c.retention_stated
    assert c.named_processors == [] and "erasure" not in c.rights_listed
    policy = " ".join((ROOT / "demo/fixture-app/privacy.html").read_text().split())
    assert c.quotes and all(q in policy for q in c.quotes.values())


def test_expected_rules_fire(report):
    assert [f.rule.split("_")[0] for f in report.findings] == ["R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "R9"]
    assert all(f.evidence for f in report.findings)
    r8 = next(f for f in report.findings if f.rule.startswith("R8"))
    assert r8.evidence[0].file == "src/app/api/chat/route.ts" and r8.evidence[0].line == 8


def test_compliant_product_has_no_findings():
    policy = (
        "We collect your email address and usage data. We share personal data with service providers such as "
        "Stripe who process it on our behalf. Some providers are outside the UK and we use standard contractual "
        "clauses for these international transfers. We retain account data for 12 months after closure. "
        "You have the right to erasure: to delete your account, go to Settings."
    )
    claims = validate_quotes(heuristic(policy), policy)
    obs = [Observation(id="obs-1", vendor="Stripe", vendor_country="US", data_categories=["email"],
                       purpose_guess="payments", evidence=[Evidence(kind="manifest", summary="stripe", file="package.json", line=3)])]  # fmt: skip
    assert run_rules(obs, claims, CodeSignals(), "https://example.com/privacy") == []


def test_quotes_not_in_policy_are_dropped():
    claims = heuristic("We never share your data with third parties.")
    claims.quotes["mentions_ai"] = "We use AI to help you."
    assert "mentions_ai" not in validate_quotes(claims, "We never share your data with third parties.").quotes


def test_sample_contract_is_current(report):
    """contracts/sample_report.json must validate and match what the pipeline produces (run `make sample`)."""
    sample = AuditReport.model_validate(json.loads((ROOT / "contracts/sample_report.json").read_text()))
    assert [f.rule for f in sample.findings] == [f.rule for f in report.findings]
    assert [(c.jurisdiction, c.area, c.status) for c in sample.matrix] == [
        (c.jurisdiction, c.area, c.status) for c in report.matrix
    ]
