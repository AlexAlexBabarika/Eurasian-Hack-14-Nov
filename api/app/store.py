"""In-memory audit state + JSON files in ./data/audits/. No database."""

import json
from pathlib import Path

from pydantic import BaseModel

from app.models import AuditReport, AuditRequest, ProgressEvent

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


def find_cached(req: AuditRequest) -> AuditState | None:
    """DEMO_MODE=cached: a finished audit with the same three URLs."""
    key = (req.repo_url.rstrip("/"), req.site_url.rstrip("/"), req.policy_url.rstrip("/"))
    for path in sorted(AUDIT_DIR.glob("*.json")):
        try:
            inputs = json.loads(path.read_text())["report"]["inputs"]
        except (KeyError, TypeError, ValueError):
            continue
        if (inputs["repo_url"].rstrip("/"), inputs["site_url"].rstrip("/"), inputs["policy_url"].rstrip("/")) == key:
            return AuditState.model_validate_json(path.read_text())
    return None
