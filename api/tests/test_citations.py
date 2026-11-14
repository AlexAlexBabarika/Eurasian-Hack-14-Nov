"""Every cited provision exists in the corpus; verdict wording and status caps are enforced in code."""

import re

from app.law.retrieve import load_corpus
from app.models import AREAS, JURISDICTIONS, Fix
from app.report.markdown import render
from app.verdict.engine import BANNED, CellProse, post_validate


def cell(report, j, area):
    return next(c for c in report.matrix if c.jurisdiction == j and c.area == area)


def test_corpus_is_well_formed():
    corpus = load_corpus()
    for j in JURISDICTIONS:
        assert len([p for p in corpus.values() if p.jurisdiction == j]) >= 10, j
        for area in ["personal_data", "ai_transparency", "consumer"]:
            assert any(p.jurisdiction == j and p.area == area for p in corpus.values()), (j, area)
    for p in corpus.values():
        assert p.id.startswith(p.jurisdiction + "-") and p.official_url.scheme == "https"
        assert not BANNED.search(p.summary)


def test_every_cited_provision_exists(report):
    corpus = load_corpus()
    for c in report.matrix:
        assert all(pid in corpus and pid in report.provisions for pid in c.provision_ids), c
        assert all(corpus[pid].jurisdiction == c.jurisdiction and corpus[pid].area == c.area for pid in c.provision_ids)
        assert all(fid in {f.id for f in report.findings} for fid in c.finding_ids)


def test_matrix_shape_and_demo_verdicts(report):
    assert len(report.matrix) == len(JURISDICTIONS) * len(AREAS)
    assert cell(report, "EU", "personal_data").status == "red"
    assert cell(report, "KZ", "ai_transparency").status == "red"
    assert cell(report, "UK", "ai_transparency").status == "amber"  # no AI statute: capped
    assert all(cell(report, j, "financial").status == "grey" for j in JURISDICTIONS)


def test_same_cookie_evidence_differs_between_uk_and_eu(report):
    r5 = next(f for f in report.findings if f.rule.startswith("R5"))
    uk, eu = cell(report, "UK", "personal_data"), cell(report, "EU", "personal_data")
    assert uk.finding_statuses[r5.id] == "amber" and eu.finding_statuses[r5.id] == "red"
    assert "UK-PECR-SCHA1-5" in uk.provision_ids and "EU-EPRIVACY-5-3" in eu.provision_ids


def test_no_banned_wording_in_generated_text(report):
    assert not BANNED.search(render(report))
    assert re.search(r"possible inconsistency with", render(report), re.I)


def test_post_validation_drops_unknown_citations_and_rejects_banned_wording(report):
    base = cell(report, "EU", "personal_data")
    ok = CellProse(headline="Mixpanel receives email", reasoning="Possible inconsistency with Art. 13(1)(e).",
                   provision_ids=["EU-GDPR-13-1-e", "EU-GDPR-99-MADE-UP", "UK-GDPR-17"],
                   fixes=[Fix(policy_clause="We use Mixpanel.", code_change=None)])  # fmt: skip
    out = post_validate(base, ok, base.provision_ids)
    assert out.provision_ids == ["EU-GDPR-13-1-e"] and out.status == base.status
    assert "EU-GDPR-99-MADE-UP" in out.unverified_notes[-1] and "UK-GDPR-17" in out.unverified_notes[-1]
    bad = ok.model_copy(update={"reasoning": "This violates GDPR."})
    assert post_validate(base, bad, base.provision_ids) == base
