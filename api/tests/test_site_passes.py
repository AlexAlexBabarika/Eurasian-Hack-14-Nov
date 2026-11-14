"""Three-pass site scan: before consent, after reject, after accept. No browser: canned SiteScans only."""

import asyncio
from unittest.mock import patch

import pytest

from app import sample
from app.claims.extract import heuristic
from app.detect import trackers
from app.detect.code_signals import CodeSignals
from app.diff.rules import run_rules
from app.ingest import consent, site
from app.ingest.site import ConsentPass, SiteScan
from app.models import AuditRequest, Finding, ProgressEvent
from app.pipeline import run_audit
from app.report.markdown import render
from app.verdict.engine import BANNED, deterministic_cell

URL = "https://acme.test/"
GA = "https://www.google-analytics.com/g/collect?v=2&tid=G-TEST&en=page_view"
HOTJAR = "https://static.hotjar.com/c/hotjar-1.js"
POLICY = "We collect your email address. We keep account data for 12 months."
POLICY_PATH = str(sample.FIXTURE / "privacy.html")


def scan_with(reject: ConsentPass | None = None, accept: ConsentPass | None = None) -> SiteScan:
    return SiteScan(url=URL, requests=[URL, GA], cookies=["_ga"], reject=reject, accept=accept)


IGNORED = scan_with(reject=ConsentPass(clicked="Reject all", requests=[URL, GA], cookies=["_ga"]),
                    accept=ConsentPass(clicked="Accept all", requests=[URL, GA, HOTJAR]))  # fmt: skip


def findings_for(scan: SiteScan) -> dict[str, Finding]:
    obs = trackers.merge([], trackers.detect(scan))
    found = run_rules(obs, heuristic(POLICY), CodeSignals(), "https://acme.test/privacy")
    return {f.rule.split("_")[0]: f for f in found}


@pytest.mark.parametrize(("label", "kind"), [
    ("Reject all", "reject"), ("Decline", "reject"), ("Deny", "reject"), ("Refuse cookies", "reject"),
    ("Only necessary", "reject"), ("Use essential cookies only", "reject"), ("Accept only necessary", "reject"),
    ("  REJECT\n ALL ", "reject"), ("Отклонить", "reject"),
    ("Accept all", "accept"), ("Allow all cookies", "accept"), ("I agree", "accept"), ("Got it", "accept"),
    ("OK", "accept"), ("Accept", "accept"), ("Принять", "accept"),
    ("Cookie settings", None), ("Allow selection", None), ("Accepted payment methods", None), ("Okta", None),
    ("Sign in", None), ("Reject all and subscribe", None), ("", None), ("Accept our terms and read the long story of how we care for you", None),
])  # fmt: skip
def test_button_labels_are_classified(label, kind):
    assert consent.button_kind(label) == kind


def test_pick_returns_the_first_matching_button():
    labels = ["Home", "Cookie settings", "Accept all", "Reject all", "Decline"]
    assert consent.pick(labels, "reject") == 3 and consent.pick(labels, "accept") == 2
    assert consent.pick(["Home", "Pricing"], "reject") is None


def test_known_cmp_buttons_are_covered():
    assert "#onetrust-reject-all-handler" in consent.CMP["reject"]
    assert "#onetrust-accept-btn-handler" in consent.CMP["accept"]
    assert "#CybotCookiebotDialogBodyButtonDecline" in consent.CMP["reject"]
    assert "#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll" in consent.CMP["accept"]


def test_tracker_seen_after_reject_gets_its_own_evidence():
    obs = {o.vendor: o for o in trackers.detect(IGNORED)}
    after = [e for e in obs["Google Analytics"].evidence if "after consent was rejected" in e.summary]
    assert {e.kind for e in after} == {"network", "cookie"} and obs["Google Analytics"].pre_consent


def test_vendor_seen_only_after_accept_is_recorded_but_not_pre_consent():
    obs = {o.vendor: o for o in trackers.merge([], trackers.detect(IGNORED))}
    assert not obs["Hotjar"].pre_consent
    assert all("after consent was accepted" in e.summary for e in obs["Hotjar"].evidence)
    assert not any("accepted" in e.summary for e in obs["Google Analytics"].evidence)


def test_tracking_after_reject_is_a_finding_with_evidence():
    found = findings_for(IGNORED)
    r10 = found["R10"]
    assert r10.rule == "R10_TRACKING_AFTER_REJECT" and r10.severity == "high"
    assert r10.areas == ["personal_data", "consumer"] and "Google Analytics" in r10.title
    assert r10.evidence and all("after consent was rejected" in e.summary for e in r10.evidence)
    assert all("before any consent" in e.summary for e in found["R5"].evidence)
    assert "Hotjar" not in r10.title and "Hotjar" not in found["R5"].title


def test_tracker_first_seen_after_reject_is_flagged_without_r5():
    scan = SiteScan(url=URL, requests=[URL], reject=ConsentPass(clicked="Decline", requests=[GA]))
    found = findings_for(scan)
    assert "R10" in found and "R5" not in found


@pytest.mark.parametrize("scan", [
    scan_with(),
    scan_with(reject=ConsentPass(), accept=ConsentPass()),
    scan_with(reject=ConsentPass(clicked="Reject all", requests=[URL]), accept=ConsentPass(clicked="OK", requests=[GA])),
    scan_with(reject=ConsentPass(error="TimeoutError: pass did not finish", requests=[GA])),
])  # fmt: skip
def test_no_finding_without_after_reject_evidence(scan):
    found = findings_for(scan)
    assert "R10" not in found and "R5" in found


def test_essential_vendor_after_reject_is_not_flagged():
    stripe = "https://js.stripe.com/v3/"
    scan = SiteScan(url=URL, requests=[URL], reject=ConsentPass(clicked="Decline", requests=[stripe]))
    assert [o.vendor for o in trackers.detect(scan)] == ["Stripe"]
    assert "R10" not in findings_for(scan)


def test_ignored_refusal_is_not_softened_in_the_uk():
    obs = trackers.merge([], trackers.detect(IGNORED))
    found = run_rules(obs, heuristic(POLICY), CodeSignals(), "https://acme.test/privacy")
    r5, r10 = (next(f for f in found if f.rule.startswith(r)) for r in ("R5_", "R10_"))
    cells = {j: deterministic_cell(j, "personal_data", found, obs) for j in ("UK", "EU", "KZ")}
    assert cells["UK"].finding_statuses[r5.id] == "amber"
    assert [cells[j].finding_statuses[r10.id] for j in ("UK", "EU", "KZ")] == ["red", "red", "amber"]
    assert "object" in cells["UK"].reasoning and "EU-EPRIVACY-5-3" in cells["EU"].provision_ids
    only_r10 = deterministic_cell("UK", "personal_data", [r10], obs)
    assert "UK-PECR-SCHA1-5" in only_r10.provision_ids and len(only_r10.provision_ids) <= 3
    fix = next(fx for fx in only_r10.fixes if fx.code_change)
    assert "Google Analytics" in fix.code_change and fix.policy_clause is None
    assert not BANNED.search(" ".join(c.reasoning + str(c.fixes) for c in cells.values()))


def run(scan: SiteScan) -> tuple:
    events: list[ProgressEvent] = []

    async def fake_scan(url: str) -> SiteScan:
        return scan

    with patch("app.ingest.site.scan", fake_scan):
        req = AuditRequest(site_url=URL, policy_url=POLICY_PATH)
        report = asyncio.run(run_audit("t", req, events.append, use_llm=False))
    return report, next(e for e in events if e.step == "site_scan" and e.status != "running")


def test_pipeline_reports_each_pass():
    scan = scan_with(reject=ConsentPass(clicked="Reject all", requests=[URL, GA]), accept=ConsentPass())
    report, event = run(scan)
    assert event.status == "done"
    assert "2 requests before consent" in event.message
    assert "after reject: Google Analytics still fires" in event.message
    assert "accept: no banner found" in event.message
    assert report.stats["requests_pre_consent"] == 2 and report.stats["requests_after_reject"] == 2
    assert report.stats["site_passes"] == {"reject": "clicked: Reject all", "accept": "no banner found"}
    assert report.stats["trackers_after_reject"] == ["Google Analytics"]
    assert "R10_TRACKING_AFTER_REJECT" in [f.rule for f in report.findings]
    assert "after reject: 2" in render(report) and not BANNED.search(render(report))


def test_failed_pass_is_reported_and_keeps_the_other_passes():
    scan = scan_with(reject=ConsentPass(error="TimeoutError: pass did not finish"),
                     accept=ConsentPass(clicked="OK", requests=[HOTJAR]))  # fmt: skip
    report, event = run(scan)
    assert event.status == "done" and "reject: failed (TimeoutError" in event.message
    assert "after accept: 1 more vendor (Hotjar)" in event.message
    assert report.stats["vendors_after_accept_only"] == ["Hotjar"]
    assert {f.rule.split("_")[0] for f in report.findings} >= {"R5"}
    assert "R10" not in {f.rule.split("_")[0] for f in report.findings}


def test_canned_scan_without_passes_is_unchanged(report, fixture_audit):
    assert "R10" not in {f.rule.split("_")[0] for f in report.findings}
    assert not {"site_passes", "requests_after_reject", "requests_after_accept"} & set(report.stats)
    event = next(e for e in fixture_audit.events if e.step == "site_scan" and e.status == "done")
    assert event.message == "4 requests before consent; trackers: Google Analytics, PostHog"


def test_a_failed_or_hung_pass_keeps_partial_evidence(monkeypatch):
    monkeypatch.setattr(site, "TIMEOUT_S", 0.05)

    async def hangs(p: ConsentPass) -> None:
        p.requests.append(GA)
        await asyncio.sleep(5)

    async def fails(p: ConsentPass) -> None:
        p.clicked = "Reject"
        raise RuntimeError("browser context closed")

    async def both() -> tuple[ConsentPass, ConsentPass]:
        a, b = ConsentPass(), ConsentPass()
        await asyncio.gather(site._bounded(hangs(a), a), site._bounded(fails(b), b))
        return a, b

    hung, failed = asyncio.run(both())
    assert hung.requests == [GA] and "TimeoutError" in hung.error
    assert failed.clicked == "Reject" and "RuntimeError" in failed.error
