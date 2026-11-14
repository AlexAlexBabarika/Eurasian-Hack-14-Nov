"""In-memory audit state + JSON files in ./data/audits/. No database."""

import json
from pathlib import Path

from pydantic import BaseModel

from app.models import AuditReport, AuditRequest, AuditSummary, ProgressEvent

AUDIT_DIR = Path(__file__).resolve().parents[1] / "data" / "audits"


class AuditState(BaseModel):
    status: str = "running"  # running | done | error
    events: list[ProgressEvent] = []
    report: AuditReport | None = None
    error: str | None = None


AUDITS: dict[str, AuditState] = {}


def save(state: AuditState, name: str | None = None) -> Path:
    assert state.report
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    path = AUDIT_DIR / f"{name or state.report.id}.json"
    path.write_text(state.model_dump_json(indent=2))
    return path


def load(audit_id: str) -> AuditState | None:
    if audit_id in AUDITS:
        return AUDITS[audit_id]
    path = AUDIT_DIR / f"{audit_id}.json"
    if audit_id.replace("-", "").isalnum() and path.exists():
        AUDITS[audit_id] = AuditState.model_validate_json(path.read_text())
        return AUDITS[audit_id]
    return None


def _key(inputs: dict) -> tuple[str, ...]:
    return tuple((inputs.get(name) or "").rstrip("/") for name in ("repo_url", "site_url", "policy_url"))


def find_cached(req: AuditRequest) -> AuditState | None:
    """DEMO_MODE=cached: a finished audit with the same three URLs."""
    key = _key(req.model_dump())
    for path in sorted(AUDIT_DIR.glob("*.json")):
        try:
            inputs = json.loads(path.read_text())["report"]["inputs"]
        except (KeyError, TypeError, ValueError):
            continue
        if _key(inputs) == key:
            return AuditState.model_validate_json(path.read_text())
    return None


def summaries(prefix: str = "demo-") -> list[AuditSummary]:
    """Saved audits whose file name starts with `prefix`: the examples shown on the landing page."""
    out: list[AuditSummary] = []
    for path in sorted(AUDIT_DIR.glob(f"{prefix}*.json")):
        try:
            report = AuditState.model_validate_json(path.read_text()).report
        except ValueError:
            continue
        if not report:
            continue
        counts = {status: 0 for status in ("red", "amber", "green", "grey")}
        for cell in report.matrix:
            counts[cell.status] += 1
        out.append(AuditSummary(
            id=path.stem, repo_url=report.inputs.get("repo_url"), site_url=report.inputs.get("site_url"),
            policy_url=report.inputs.get("policy_url") or "", findings=len(report.findings),
            vendors=len([o for o in report.observations if o.vendor]), status_counts=counts,
        ))  # fmt: skip
    return out
