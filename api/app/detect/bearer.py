"""Run Bearer CLI (if installed) and parse its dataflow report. Any failure → empty result, pipeline continues."""

import asyncio
import json
import re
import shutil
from pathlib import Path

from pydantic import BaseModel

from app.models import Evidence

TIMEOUT_S = 90
# Only the rules that report personal data reaching a logger; data types are classified regardless of rules, and
# skipping Bearer's other security rules makes the scan ~3x faster on a real repo. Bearer rejects rule ids for
# languages absent from the repo, so those are dropped and the scan retried.
_RULES = ("javascript_lang_logger", "python_lang_logger", "go_lang_logger")
_INVALID_RULES = re.compile(r"invalid rule IDs in only option: ([\w,]+)")
_PII_TYPES = {"email address": "email", "telephone number": "phone", "fullname": "name", "firstname": "name",
              "lastname": "name", "physical address": "location", "geographic": "location", "ip address": "ip",
              "device identifier": "device_id", "browser fingerprint": "device_id", "credit card number": "payment",
              "bank account": "payment", "browsing behavior": "usage"}  # fmt: skip
_PII_CATEGORIES = {"medical and health": "health", "location": "location"}


class BearerResult(BaseModel):
    ran: bool = False
    message: str = "Bearer CLI not installed; using manifest detector only"
    data_types: dict[str, list[Evidence]] = {}  # our category → evidence
    pii_logs: list[Evidence] = []


def _category(dt: dict) -> str | None:
    return _PII_TYPES.get(str(dt.get("name", "")).lower()) or _PII_CATEGORIES.get(
        str(dt.get("category_name", "")).lower()
    )


def _evidence(loc: dict, summary: str, snippet: str | None = None) -> Evidence:
    return Evidence(
        kind="bearer",
        summary=summary,
        file=loc.get("filename") or loc.get("full_filename"),
        line=loc.get("start_line_number") or loc.get("line_number"),
        snippet=snippet,
    )


def parse(report: dict) -> BearerResult:
    out = BearerResult(ran=True, message="")
    for dt in report.get("data_types") or []:
        cat = _category(dt)
        if not cat:
            continue
        for det in dt.get("detectors") or []:
            for loc in (det.get("locations") or [])[:3]:
                out.data_types.setdefault(cat, []).append(_evidence(loc, f"Bearer: {dt['name']} processed"))
    seen: set[tuple[str | None, int | None]] = set()
    for risk in report.get("risks") or []:
        if not str(risk.get("detector_id", "")).endswith(
            "_logger"
        ):  # *_logger_leak flags any variable, not PII
            continue
        for loc in risk.get("locations") or []:
            types = sorted({str(t.get("name")) for t in loc.get("data_types") or [] if t.get("name")})
            ev = _evidence(
                loc,
                f"Bearer: {', '.join(types) or 'personal data'} written to logs",
                ((loc.get("source") or {}).get("content") or loc.get("content") or "")[:300] or None,
            )
            ev.line = (loc.get("source") or {}).get(
                "start_line_number"
            ) or ev.line  # one statement, many fields
            if (ev.file, ev.line) not in seen and len(out.pii_logs) < 5:
                seen.add((ev.file, ev.line))
                out.pii_logs.append(ev)
    out.message = f"Bearer found {len(out.data_types)} personal data types"
    if out.pii_logs:
        out.message += f" and {len(out.pii_logs)} log statements with personal data"
    return out


async def run(repo_dir: Path) -> BearerResult:
    if not shutil.which("bearer"):
        return BearerResult()
    loop = asyncio.get_running_loop()
    deadline = loop.time() + TIMEOUT_S
    rules = list(_RULES)
    try:
        while True:
            args = [
                "scan",
                str(repo_dir),
                "--report",
                "dataflow",
                "--format",
                "json",
                "--quiet",
                "--disable-version-check",
            ]
            if rules:
                args += ["--only-rule", ",".join(rules)]
            proc = await asyncio.create_subprocess_exec(
                "bearer", *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), max(deadline - loop.time(), 1))
            except TimeoutError:
                proc.kill()
                return BearerResult(message=f"Bearer timed out after {TIMEOUT_S}s; skipped")
            invalid = _INVALID_RULES.search(stderr.decode(errors="replace")) if rules else None
            if invalid:
                rules = [r for r in rules if r not in invalid.group(1).split(",")]
                continue
            return parse(json.loads(stdout))
    except Exception as e:  # noqa: BLE001 - Bearer is optional, never fail the audit on it
        return BearerResult(message=f"Bearer failed ({type(e).__name__}); skipped")
