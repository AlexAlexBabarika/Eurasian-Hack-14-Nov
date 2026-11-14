"""Run Bearer CLI (if installed) and parse its dataflow report. Any failure → empty result, pipeline continues."""

import asyncio
import json
import shutil
from pathlib import Path

from pydantic import BaseModel

from app.models import Evidence

TIMEOUT_S = 90
_PII_TYPES = {"email address": "email", "telephone number": "phone", "fullname": "name", "firstname": "name",
              "lastname": "name", "physical address": "location", "passwords": "password"}  # fmt: skip


class BearerResult(BaseModel):
    ran: bool = False
    message: str = "Bearer CLI not installed; using manifest detector only"
    data_types: dict[str, list[Evidence]] = {}  # our category → evidence
    pii_logs: list[Evidence] = []


def parse(report: dict) -> BearerResult:
    out = BearerResult(ran=True, message="")
    for dt in report.get("data_types") or []:
        cat = _PII_TYPES.get(str(dt.get("name", "")).lower())
        if not cat:
            continue
        for det in dt.get("detectors") or []:
            for loc in (det.get("locations") or [])[:3]:
                out.data_types.setdefault(cat, []).append(Evidence(
                    kind="bearer", summary=f"Bearer: {dt['name']} processed",
                    file=loc.get("filename") or loc.get("full_filename"),
                    line=loc.get("start_line_number") or loc.get("line_number"),
                ))  # fmt: skip
    for risk in report.get("risks") or []:
        if "logger" not in str(risk.get("detector_id", "")):
            continue
        for loc in (risk.get("locations") or [])[:3]:
            out.pii_logs.append(Evidence(
                kind="bearer", summary=f"Bearer: personal data in logs ({risk['detector_id']})",
                file=loc.get("filename") or loc.get("full_filename"),
                line=loc.get("start_line_number") or loc.get("line_number"),
                snippet=loc.get("content"),
            ))  # fmt: skip
    out.message = f"Bearer found {len(out.data_types)} personal data types"
    return out


async def run(repo_dir: Path) -> BearerResult:
    if not shutil.which("bearer"):
        return BearerResult()
    try:
        proc = await asyncio.create_subprocess_exec(
            "bearer", "scan", str(repo_dir), "--report", "dataflow", "--format", "json", "--quiet",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )  # fmt: skip
        try:
            stdout, _ = await asyncio.wait_for(proc.communicate(), TIMEOUT_S)
        except TimeoutError:
            proc.kill()
            return BearerResult(message=f"Bearer timed out after {TIMEOUT_S}s; skipped")
        return parse(json.loads(stdout))
    except Exception as e:  # noqa: BLE001 - Bearer is optional, never fail the audit on it
        return BearerResult(message=f"Bearer failed ({type(e).__name__}); skipped")
