"""Findings × provisions → CellVerdicts. Status is deterministic; the LLM (if configured) writes the prose."""

import asyncio
import re
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, NamedTuple

from pydantic import BaseModel, StringConstraints, model_validator

from app import llm
from app.detect.trackers import AFTER_REJECT, seen
from app.law.retrieve import RULE_TAGS, load_corpus, retrieve
from app.models import AREAS, Area, CellVerdict, Finding, Fix, Jurisdiction, Observation, Provision, Status
from app.verdict.fixes import PURPOSE, template_fixes

PROMPTS = Path(__file__).parent / "prompts"
SYSTEM = (PROMPTS / "verdict.md").read_text() + "\n" + (PROMPTS / "fix.md").read_text()
BANNED = re.compile(r"\bviolat|\billegal|\bunlawful|\bbreach(?:es|ed)? (?:of )?(?:the )?(?:law|gdpr|act)", re.I)
MAX_TOKENS = 1500  # a cell is a headline, 2-4 sentences and up to three fixes
RANK: dict[Status, int] = {"grey": 0, "green": 1, "amber": 2, "red": 3}
EU_EEA = {"AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU",
          "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE", "IS", "LI", "NO"}  # fmt: skip
HOME = {"UK": {"UK", "GB"}, "EU": EU_EEA, "KZ": {"KZ"}}
AREA_LABEL = {"personal_data": "personal data", "ai_transparency": "AI transparency", "consumer": "consumer protection",
              "financial": "financial licensing"}  # fmt: skip


HEADLINE_MAX = 90
DATA_LABEL = {"email": "email address", "name": "name", "phone": "phone number", "usage": "usage data",
              "device_id": "device ID", "ip": "IP address", "user_content": "user content", "payment": "payment data",
              "location": "location", "health": "health data"}  # fmt: skip
_RAW_DATA_ID = re.compile(r"\b(?:device_id|user_content|ip)\b")
_IDENTIFIER = re.compile(r"\b[A-Za-z0-9]+_\w+|\b(?:UK|EU|KZ)-[A-Z0-9]+-[\w-]+|\b[FR]\d+\b")
_NUMBER_WORD = re.compile(r"\b(?:two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\b", re.I)


def humanize(text: str) -> str:
    """Raw data-category ids in rule output → the labels a founder reads."""
    return _RAW_DATA_ID.sub(lambda m: DATA_LABEL[m.group(0)], text)


def headline_problems(headline: str) -> list[str]:
    problems = []
    if len(headline) > HEADLINE_MAX:
        problems.append(f"headline is {len(headline)} characters; the limit is {HEADLINE_MAX}")
    if m := _IDENTIFIER.search(headline):
        problems.append(f"headline contains the identifier `{m.group(0)}`; use a human label instead")
    if m := _NUMBER_WORD.search(headline):
        problems.append(f'headline spells out the number "{m.group(0)}"; write numbers as digits')
    return problems


def short_headline(title: str) -> str:
    """A finding title as a cell headline: human labels, no trailing list, at most HEADLINE_MAX characters."""
    text = humanize(title)
    if len(text) > HEADLINE_MAX:
        text = re.sub(r"\s*\([^()]*\)$", "", text)
    if len(text) > HEADLINE_MAX:
        text = text[:HEADLINE_MAX].rsplit(" ", 1)[0].rstrip(",;:") + "…"
    return text


class CellProse(BaseModel):
    headline: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    reasoning: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    provision_ids: list[str]
    fixes: list[Fix]

    @model_validator(mode="after")
    def _house_rules(self) -> "CellProse":
        """Raising here sends the reasons back to the model for its one retry (see llm.structured)."""
        problems = headline_problems(self.headline)
        if BANNED.search(_prose_text(self)):
            problems.append('text states that a law is broken; write "possible inconsistency with" instead')
        if problems:
            raise ValueError("; ".join(problems))
        return self


def _prose_text(prose: CellProse) -> str:
    return " ".join([prose.headline, prose.reasoning, *(f"{fx.policy_clause} {fx.code_change}" for fx in prose.fixes)])


class Matrix(NamedTuple):
    cells: list[CellVerdict]
    provisions: dict[str, Provision]  # every provision cited by a cell
    method: str  # "llm" or "deterministic"
    llm_cells: int = 0  # cells the LLM was asked to write
    fallbacks: int = 0  # of those, cells that kept the template text (call failed twice or prose was rejected)


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
    if rule == "R10":
        if j == "UK":
            note = ("UK: the statistical-purposes exception in the Data (Use and Access) Act 2025 still requires a "
                    "simple way to object, so it does not cover trackers that keep firing after a refusal.")  # fmt: skip
        elif j == "EU":
            note = "EU: non-essential cookies or trackers need consent, and here consent was refused."
        elif j == "KZ":
            status = "amber"
            note = ("Kazakhstan has no cookie-specific rule; general consent requirements for collection apply, "
                    "and here consent was refused.")  # fmt: skip
    if area == "ai_transparency" and j == "UK":
        status = "amber" if RANK[status] > RANK["amber"] else status
        note = "UK has no AI-specific statute; this cell relies on ICO guidance, so status is capped at amber."
    return status, note


def _provisions(f: Finding, j: Jurisdiction, area: Area) -> list[Provision]:
    """law/retrieve.py has no tags for R10 yet; until it does, R10 is looked up under the R5 cookie and tracking tags."""
    if f.rule == "R10_TRACKING_AFTER_REJECT" and f.rule not in RULE_TAGS:
        f = f.model_copy(update={"rule": "R5_TRACKING_BEFORE_CONSENT"})
    return retrieve(f, j, area)


def _dedupe(items: list[Provision]) -> list[Provision]:
    return list({p.id: p for p in items}.values())


def deterministic_cell(j: Jurisdiction, area: Area, findings: list[Finding], observations: list[Observation],
                       gaps: list[str] | None = None) -> CellVerdict:  # fmt: skip
    """`gaps` says which inputs are missing or unreadable (repository, policy); a cell with gaps is never green."""
    if area == "financial":
        return CellVerdict(
            jurisdiction=j, area=area, status="grey", headline="Needs questionnaire",
            reasoning="Financial licensing cannot be assessed from code and policy alone. Out of scope for this scan.",
            finding_ids=[], provision_ids=[], fixes=[],
        )  # fmt: skip
    rows = []
    for f in findings:
        if area in f.areas and (res := finding_status(f, j, area, observations)):
            rows.append((f, res[0], res[1], _provisions(f, j, area)))
    if not rows and gaps:
        return CellVerdict(
            jurisdiction=j, area=area, status="grey", finding_ids=[], provision_ids=[], fixes=[],
            headline=f"Not assessed: {' and '.join(gaps)}",
            reasoning="No findings, but the scan was incomplete, so this is not a clean result. Complete the inputs "
            "and run the audit again.",
        )  # fmt: skip
    if not rows:
        return CellVerdict(
            jurisdiction=j, area=area, status="green", finding_ids=[], provision_ids=[], fixes=[],
            headline=f"No possible inconsistencies detected for {AREA_LABEL[area]}",
            reasoning="None of the checks we ran (R1-R10) produced a finding for this cell. This reflects only what "
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
        jurisdiction=j, area=area, status=status, headline=short_headline(rows[0][0].title), reasoning=" ".join(sentences),
        finding_ids=[r[0].id for r in rows], provision_ids=[p.id for p in provisions], fixes=fixes,
        unverified_notes=notes, finding_statuses={r[0].id: r[1] for r in rows},
    )  # fmt: skip


def post_validate(cell: CellVerdict, prose: CellProse, allowed: list[str]) -> CellVerdict:
    """Enforce in code what the prompt asks for. Reject the prose entirely if it uses banned wording."""
    if BANNED.search(_prose_text(prose)) or headline_problems(prose.headline):
        return cell
    kept = [pid for pid in prose.provision_ids if pid in allowed and pid in load_corpus()]
    dropped = [pid for pid in prose.provision_ids if pid not in kept]
    out = cell.model_copy(deep=True)
    out.headline, out.reasoning = prose.headline, prose.reasoning
    out.provision_ids = list(dict.fromkeys(kept)) or cell.provision_ids
    out.fixes = [fx for fx in prose.fixes if fx.policy_clause or fx.code_change][:4] or cell.fixes
    if dropped:
        out.unverified_notes.append(f"Dropped citations not in the curated corpus: {', '.join(dropped)}")
    return out


def _prompt(cell: CellVerdict, findings: list[Finding], observations: list[Observation]) -> str:
    corpus = load_corpus()
    parts = [f"Jurisdiction: {cell.jurisdiction}\nLegal area: {AREA_LABEL[cell.area]}\nCell status (fixed): {cell.status}",
             f"Jurisdiction notes from the rules engine:\n{humanize(cell.reasoning)}", "<findings>"]  # fmt: skip
    for f in findings:
        if f.id not in cell.finding_ids:
            continue
        parts.append(f"- {humanize(f.title)} (status here: {cell.finding_statuses.get(f.id)})")
        for o in observations:
            if o.id in f.observation_ids:
                when = "; requests or cookies seen on the site before any consent interaction" if o.pre_consent else ""
                when += "; still seen after the visitor rejected cookies" if seen(o, AFTER_REJECT) else ""
                purpose = PURPOSE.get(o.purpose_guess or "", "service provider")
                data = ", ".join(DATA_LABEL.get(c, c.replace("_", " ")) for c in o.data_categories) or "not known"
                parts.append(f"  vendor: {o.vendor} ({o.vendor_country}), used for {purpose}, receives: {data}{when}")
        for e in f.evidence[:6]:
            loc = f"{e.file}:{e.line}" if e.file else (e.url or "")
            parts.append(f"  evidence ({e.kind}) {loc}: {e.summary}" + (f' | quote: "{e.quote}"' if e.quote else ""))
    parts.append("</findings>\n<provisions>")
    parts += [f"[{pid}] {corpus[pid].instrument}, {corpus[pid].ref}: {corpus[pid].summary}" for pid in cell.provision_ids]
    parts.append("</provisions>")
    return "\n".join(parts)


async def build_matrix(findings: list[Finding], observations: list[Observation], jurisdictions: list[Jurisdiction],
                       use_llm: bool = True, gaps: list[str] | None = None,
                       on_cell: Callable[[int, int], None] | None = None, model: str | None = None,
                       ) -> Matrix:  # fmt: skip
    """With an LLM, `on_cell(finished, total)` is called each time a cell is finished."""
    cells = [deterministic_cell(j, a, findings, observations, gaps) for j in jurisdictions for a in AREAS]
    method = "deterministic"
    llm_cells = fallbacks = 0

    async def refine(cell: CellVerdict) -> CellVerdict:
        nonlocal llm_cells, fallbacks
        if not cell.finding_ids or not cell.provision_ids:
            return cell
        llm_cells += 1
        try:
            # Status and citations are decided in code; the model only writes prose, so it needs no reasoning pass.
            prose = await llm.structured(SYSTEM, _prompt(cell, findings, observations), CellProse,
                                         max_tokens=MAX_TOKENS, reasoning=False, model=model)  # fmt: skip
            out = post_validate(cell, prose, cell.provision_ids)
        except Exception:  # noqa: BLE001 - deterministic cell is always a valid answer
            out = cell
        fallbacks += out is cell
        return out

    finished = 0

    async def tracked(cell: CellVerdict) -> CellVerdict:
        nonlocal finished
        out = await refine(cell)
        finished += 1
        if on_cell:
            on_cell(finished, len(cells))
        return out

    if use_llm and llm.available():
        cells = list(await asyncio.gather(*(tracked(c) for c in cells)))
        method = "llm"
    corpus = load_corpus()
    cited = {pid: corpus[pid] for c in cells for pid in c.provision_ids}
    return Matrix(cells, cited, method, llm_cells, fallbacks)
