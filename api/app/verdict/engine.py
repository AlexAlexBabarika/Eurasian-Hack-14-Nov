"""Findings × provisions → CellVerdicts. Status is deterministic; the LLM (if configured) writes the prose."""

import asyncio
import re
from pathlib import Path

from pydantic import BaseModel

from app import llm
from app.law.retrieve import load_corpus, retrieve
from app.models import AREAS, Area, CellVerdict, Finding, Fix, Jurisdiction, Observation, Provision, Status
from app.verdict.fixes import template_fixes

PROMPTS = Path(__file__).parent / "prompts"
SYSTEM = (PROMPTS / "verdict.md").read_text() + "\n" + (PROMPTS / "fix.md").read_text()
BANNED = re.compile(r"\bviolat|\billegal|\bunlawful|\bbreach(?:es|ed)? (?:of )?(?:the )?(?:law|gdpr|act)", re.I)
RANK: dict[Status, int] = {"grey": 0, "green": 1, "amber": 2, "red": 3}
EU_EEA = {"AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU",
          "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE", "IS", "LI", "NO"}  # fmt: skip
HOME = {"UK": {"UK", "GB"}, "EU": EU_EEA, "KZ": {"KZ"}}
AREA_LABEL = {"personal_data": "personal data", "ai_transparency": "AI transparency", "consumer": "consumer protection",
              "financial": "financial licensing"}  # fmt: skip


class CellProse(BaseModel):
    headline: str
    reasoning: str
    provision_ids: list[str]
    fixes: list[Fix]


def finding_status(f: Finding, j: Jurisdiction, area: Area, observations: list[Observation]) -> tuple[Status, str] | None:
    """Status of one finding in one cell plus a jurisdiction note. None = does not apply in this jurisdiction."""
    obs = [o for o in observations if o.id in f.observation_ids]
    status: Status = "red" if f.severity == "high" else "amber"
    note = ""
    rule = f.rule.split("_")[0]
    if rule == "R6":
        abroad = [o for o in obs if o.vendor_country not in HOME[j]]
        if not abroad:
            return None
        if j == "KZ":
            status = "red"
            note = ("Kazakhstan requires personal data to be stored in a database located in Kazakhstan and "
                    "restricts cross-border transfer; confirm where data of Kazakhstan users is stored.")  # fmt: skip
    if rule == "R5":
        if j == "UK":
            if all(o.purpose_guess == "analytics" for o in obs):
                status = "amber"
                note = ("UK: since the Data (Use and Access) Act 2025, analytics used solely for statistical purposes "
                        "to improve the service may not need consent, if users get clear information and a simple way "
                        "to object. The same evidence is treated more strictly in the EU.")  # fmt: skip
            else:
                note = "UK: the statistical-purposes exception does not cover advertising or session-recording trackers."
        elif j == "EU":
            note = "EU: consent is required before non-essential cookies or trackers, including analytics."
        elif j == "KZ":
            status = "amber"
            note = "Kazakhstan has no cookie-specific rule; general consent requirements for collection apply."
    if area == "ai_transparency" and j == "UK":
        status = "amber" if RANK[status] > RANK["amber"] else status
        note = "UK has no AI-specific statute; this cell relies on ICO guidance, so status is capped at amber."
    return status, note


def _dedupe(items: list[Provision]) -> list[Provision]:
    return list({p.id: p for p in items}.values())


def deterministic_cell(j: Jurisdiction, area: Area, findings: list[Finding], observations: list[Observation],
                       gaps: list[str] | None = None) -> CellVerdict:  # fmt: skip
    """`gaps` lists inputs that could not be read (repository, policy); a cell with gaps is never green."""
    if area == "financial":
        return CellVerdict(
            jurisdiction=j, area=area, status="grey", headline="Needs questionnaire",
            reasoning="Financial licensing cannot be assessed from code and policy alone. Out of scope for this scan.",
            finding_ids=[], provision_ids=[], fixes=[],
        )  # fmt: skip
    rows = []
    for f in findings:
        if area in f.areas and (res := finding_status(f, j, area, observations)):
            rows.append((f, res[0], res[1], retrieve(f, j, area)))
    if not rows and gaps:
        return CellVerdict(
            jurisdiction=j, area=area, status="grey", finding_ids=[], provision_ids=[], fixes=[],
            headline=f"Not assessed: {' and '.join(gaps)} could not be read",
            reasoning="No findings, but the scan was incomplete, so this is not a clean result. Fix the input and "
            "run the audit again.",
        )  # fmt: skip
    if not rows:
        return CellVerdict(
            jurisdiction=j, area=area, status="green", finding_ids=[], provision_ids=[], fixes=[],
            headline=f"No possible inconsistencies detected for {AREA_LABEL[area]}",
            reasoning="None of the checks we ran (R1-R9) produced a finding for this cell. This reflects only what "
            "was visible in the repository, the public site and the policy text.",
        )  # fmt: skip
    rows.sort(key=lambda r: -RANK[r[1]])
    status = rows[0][1]
    provisions = _dedupe([p for r in rows for p in r[3]])
    notes: list[str] = []
    if not provisions:
        status = "amber" if RANK[status] > RANK["amber"] else status
        notes.append("No provision in the curated corpus covers these findings for this jurisdiction; "
                     "the legal mapping is unverified.")  # fmt: skip
    elif not any(p.verified for p in provisions):
        notes.append("All cited provisions are awaiting human verification against the official text.")
    sentences = []
    for f, _, note, provs in rows[:4]:
        refs = "; ".join(f"{p.instrument.split(' (')[0]} {p.ref}" if j != "KZ" else f"{p.ref} ({p.title})"
                         for p in provs)  # fmt: skip
        s = f"{f.title}." + (f" Possible inconsistency with {refs}." if refs else "")
        sentences.append(s + (f" {note}" if note else ""))
    if len(rows) > 4:
        sentences.append(f"{len(rows) - 4} more findings are listed below.")
    fixes = [fx for f, *_ in rows for fx in template_fixes(f, j, observations)]
    return CellVerdict(
        jurisdiction=j, area=area, status=status, headline=rows[0][0].title, reasoning=" ".join(sentences),
        finding_ids=[r[0].id for r in rows], provision_ids=[p.id for p in provisions], fixes=fixes,
        unverified_notes=notes, finding_statuses={r[0].id: r[1] for r in rows},
    )  # fmt: skip


def post_validate(cell: CellVerdict, prose: CellProse, allowed: list[str]) -> CellVerdict:
    """Enforce in code what the prompt asks for. Reject the prose entirely if it uses banned wording."""
    text = " ".join([prose.headline, prose.reasoning, *(f"{fx.policy_clause} {fx.code_change}" for fx in prose.fixes)])
    if BANNED.search(text) or not prose.headline.strip() or not prose.reasoning.strip():
        return cell
    kept = [pid for pid in prose.provision_ids if pid in allowed and pid in load_corpus()]
    dropped = [pid for pid in prose.provision_ids if pid not in kept]
    out = cell.model_copy(deep=True)
    out.headline, out.reasoning = prose.headline.strip()[:200], prose.reasoning.strip()
    out.provision_ids = list(dict.fromkeys(kept)) or cell.provision_ids
    out.fixes = [fx for fx in prose.fixes if fx.policy_clause or fx.code_change][:4] or cell.fixes
    if dropped:
        out.unverified_notes.append(f"Dropped citations not in the curated corpus: {', '.join(dropped)}")
    return out


def _prompt(cell: CellVerdict, findings: list[Finding], observations: list[Observation]) -> str:
    corpus = load_corpus()
    parts = [f"Jurisdiction: {cell.jurisdiction}\nLegal area: {AREA_LABEL[cell.area]}\nCell status (fixed): {cell.status}",
             f"Jurisdiction notes from the rules engine:\n{cell.reasoning}", "<findings>"]  # fmt: skip
    for f in findings:
        if f.id not in cell.finding_ids:
            continue
        parts.append(f"[{f.id}] {f.rule} (status here: {cell.finding_statuses.get(f.id)}): {f.title}")
        for o in observations:
            if o.id in f.observation_ids:
                seen = "; requests or cookies seen on the site before any consent interaction" if o.pre_consent else ""
                parts.append(f"  vendor: {o.vendor} ({o.vendor_country}), purpose {o.purpose_guess}, "
                             f"data {o.data_categories}{seen}")  # fmt: skip
        for e in f.evidence[:6]:
            loc = f"{e.file}:{e.line}" if e.file else (e.url or "")
            parts.append(f"  evidence ({e.kind}) {loc}: {e.summary}" + (f' | quote: "{e.quote}"' if e.quote else ""))
    parts.append("</findings>\n<provisions>")
    parts += [f"[{pid}] {corpus[pid].instrument}, {corpus[pid].ref}: {corpus[pid].summary}" for pid in cell.provision_ids]
    parts.append("</provisions>")
    return "\n".join(parts)


async def build_matrix(findings: list[Finding], observations: list[Observation], jurisdictions: list[Jurisdiction],
                       use_llm: bool = True, gaps: list[str] | None = None,
                       ) -> tuple[list[CellVerdict], dict[str, Provision], str]:  # fmt: skip
    """Returns (matrix, cited provisions, method) where method is 'llm' or 'deterministic'."""
    cells = [deterministic_cell(j, a, findings, observations, gaps) for j in jurisdictions for a in AREAS]
    method = "deterministic"

    async def refine(cell: CellVerdict) -> CellVerdict:
        if not cell.finding_ids or not cell.provision_ids:
            return cell
        try:
            prose = await llm.structured(SYSTEM, _prompt(cell, findings, observations), CellProse)
            return post_validate(cell, prose, cell.provision_ids)
        except Exception:  # noqa: BLE001 - deterministic cell is always a valid answer
            return cell

    if use_llm and llm.available():
        cells = list(await asyncio.gather(*(refine(c) for c in cells)))
        method = "llm"
    corpus = load_corpus()
    cited = {pid: corpus[pid] for c in cells for pid in c.provision_ids}
    return cells, cited, method
