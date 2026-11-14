"""Regenerate contracts/sample_report.json and the cached demo audit from demo/fixture-app.

Offline and deterministic: no git clone, no browser, no LLM. The site scan is replaced by the requests and
cookies the fixture page is known to produce. Run: `make sample`.
"""

import asyncio
from pathlib import Path
from unittest.mock import patch

from app import store
from app.ingest.site import SiteScan
from app.models import AuditRequest
from app.pipeline import run_audit
from app.store import AuditState

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "demo" / "fixture-app"
SITE_URL = "http://localhost:4100/public/index.html"
POLICY_URL = "http://localhost:4100/privacy.html"
FIXED_POLICY = "privacy-fixed.html"  # the same product after the suggested policy clauses are pasted in
REPO_URL = "https://github.com/AlexAlexBabarika/Eurasian-Hack-14-Nov/tree/main/demo/fixture-app"

FIXTURE_SCAN = SiteScan(
    url=SITE_URL,
    requests=[
        SITE_URL,
        "https://www.googletagmanager.com/gtag/js?id=G-DEMO000000",
        "https://eu.i.posthog.com/e/?ip=1&_=1700000000000",
        "https://www.google-analytics.com/g/collect?v=2&tid=G-DEMO000000&en=page_view",
    ],
    cookies=["_ga", "ph_phc_demo_key_posthog"],
)


async def build(audit_id: str = "demo-fixture", policy: str = "privacy.html") -> AuditState:
    """Run the real pipeline on the local fixture with a canned site scan and no LLM."""
    state = AuditState()
    policy_url = POLICY_URL.replace("privacy.html", policy)
    req = AuditRequest(repo_url=str(FIXTURE), site_url=SITE_URL, policy_url=str(FIXTURE / policy))

    async def fake_scan(url: str) -> SiteScan:
        return FIXTURE_SCAN

    with patch("app.ingest.site.scan", fake_scan):
        report = await run_audit(audit_id, req, state.events.append, use_llm=False)
    # Present the public URLs a demo user would paste, not local paths.
    report.inputs.update(repo_url=REPO_URL, policy_url=policy_url)
    text = report.model_dump_json().replace(str(FIXTURE / policy), policy_url)
    state.report = type(report).model_validate_json(text)
    state.report.stats["duration_s"] = 41.3
    state.status = "done"
    return state


if __name__ == "__main__":
    state = asyncio.run(build())
    (ROOT / "contracts" / "sample_report.json").write_text(state.report.model_dump_json(indent=2) + "\n")
    print("wrote contracts/sample_report.json and", store.save(state, "demo-fixture").relative_to(ROOT))
    fixed = asyncio.run(build("demo-fixture-fixed", FIXED_POLICY))
    print("wrote", store.save(fixed, "demo-fixture-fixed").relative_to(ROOT))
