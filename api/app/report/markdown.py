"""AuditReport → Markdown export."""

from app.models import AREAS, AuditReport, Evidence, Status

RANK: dict[Status, int] = {"grey": 0, "green": 1, "amber": 2, "red": 3}

AREA_LABEL = {"personal_data": "Personal data", "ai_transparency": "AI transparency", "consumer": "Consumer protection",
              "financial": "Financial"}  # fmt: skip


def _evidence(e: Evidence) -> str:
    loc = f"`{e.file}:{e.line}`" if e.file and e.line else (f"`{e.file}`" if e.file else (e.url or ""))
    line = f"- **{e.kind}** {loc}: {e.summary}"
    if e.quote:
        line += f'\n  > "{e.quote}"'
    return line


def finding_status_by_jurisdiction(r: AuditReport, finding_id: str) -> dict[str, Status]:
    """Worst status of one finding across the areas of each jurisdiction. A jurisdiction is absent if it does not apply."""
    out: dict[str, Status] = {}
    for c in r.matrix:
        s = c.finding_statuses.get(finding_id)
        if s and (c.jurisdiction not in out or RANK[s] > RANK[out[c.jurisdiction]]):
            out[c.jurisdiction] = s
    return out


def render(r: AuditReport) -> str:
    out = ["# Groundtruth audit report", "", f"> {r.disclaimer}", ""]
    out += [f"- Repository: {r.inputs.get('repo_url') or 'not given'}", f"- Site: {r.inputs.get('site_url') or 'not given'}",
            f"- Policy: {r.inputs.get('policy_url') or 'not given'}",
            f"- Files scanned: {r.stats.get('files_scanned')}, vendors found: {r.stats.get('vendors_found')}, "
            f"requests before consent: {r.stats.get('requests_pre_consent')}" + "".join(
                f", after {p}: {r.stats[k]}" for p in ("reject", "accept") if (k := f"requests_after_{p}") in r.stats), ""]  # fmt: skip

    jurisdictions = list(dict.fromkeys(c.jurisdiction for c in r.matrix))
    cell = {(c.jurisdiction, c.area): c for c in r.matrix}
    out += ["## Matrix", "", "| | " + " | ".join(AREA_LABEL[a] for a in AREAS) + " |", "|---|" + "---|" * len(AREAS)]
    out += [f"| **{j}** | " + " | ".join(cell[(j, a)].status.upper() for a in AREAS) + " |" for j in jurisdictions]

    grey = [f"- {c.jurisdiction} / {AREA_LABEL[c.area]}: {c.headline}" for c in r.matrix
            if c.status == "grey" and c.area != "financial"]  # fmt: skip
    out += ["", *grey] if grey else []

    out += ["", "## Findings", ""]
    for f in r.findings:
        out += [f"### {f.id}. {f.title}", "", f"Rule `{f.rule}`, severity {f.severity}, areas: {', '.join(f.areas)}", ""]
        if by_jurisdiction := finding_status_by_jurisdiction(r, f.id):
            out += ["Status by jurisdiction: " + ", ".join(f"{j} {s.upper()}" for j, s in by_jurisdiction.items()), ""]
        out += [_evidence(e) for e in f.evidence] + [""]

    out += ["## Verdicts", ""]
    for c in r.matrix:
        if c.area == "financial" or not c.finding_ids:
            continue
        out += [f"### {c.jurisdiction} / {AREA_LABEL[c.area]}: {c.status.upper()}", "", f"**{c.headline}**", "",
                c.reasoning, ""]  # fmt: skip
        if c.provision_ids:
            out.append("Provisions:")
            for pid in c.provision_ids:
                p = r.provisions[pid]
                flag = "" if p.verified else " (unverified: check the official text)"
                out.append(f"- [{p.instrument}, {p.ref}]({p.official_url}): {p.title}{flag}")
            out.append("")
        out += [f"- Note: {n}" for n in c.unverified_notes]
        for i, fx in enumerate(c.fixes, 1):
            if fx.policy_clause:
                out += ["", f"Fix {i}, policy clause:", "", f"> {fx.policy_clause}"]
            if fx.code_change:
                out += ["", f"Fix {i}, code change: {fx.code_change}"]
        out.append("")
    return "\n".join(out).rstrip() + "\n"
