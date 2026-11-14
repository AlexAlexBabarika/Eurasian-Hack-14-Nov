"""Run one audit from the command line and exit non-zero on a bad result, so it can gate a CI job.

    uv run --project api python -m app.cli --repo . --policy docs/privacy.html --fail-on red

--repo and --policy accept local paths or URLs; --policy is optional. --site is optional; without it no browser is started.
"""

import argparse
import asyncio
import sys
from pathlib import Path

from app.models import AREAS, JURISDICTIONS, AuditReport, AuditRequest, ProgressEvent
from app.pipeline import run_audit
from app.report.markdown import finding_status_by_jurisdiction, render
from app.verdict.engine import RANK

EXIT_FAILED_GATE = 1
EXIT_INCOMPLETE = 2


def _args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="groundtruth", description=__doc__.splitlines()[0])
    p.add_argument("--policy", help="privacy policy: URL or local HTML/text file (optional; without it only the "
                   "checks that need no policy run)")  # fmt: skip
    p.add_argument("--repo", help="repository: local directory or public GitHub URL")
    p.add_argument("--site", help="live site URL (optional; loads it in a headless browser)")
    p.add_argument("--jurisdictions", default=",".join(JURISDICTIONS), help="comma-separated, default: %(default)s")
    p.add_argument("--fail-on", choices=["red", "amber", "never"], default="red",
                   help="exit 1 if any cell is at least this bad (default: %(default)s)")  # fmt: skip
    p.add_argument("--markdown", type=Path, help="write the full Markdown report to this file")
    p.add_argument("--json", type=Path, help="write the AuditReport JSON to this file")
    p.add_argument("--effort", choices=["fast", "strong"], default="fast",
                   help="LLM to use: MODEL_FAST or MODEL_STRONG (default: %(default)s)")  # fmt: skip
    p.add_argument("--no-llm", action="store_true", help="deterministic run even if LLM_API_KEY is set")
    args = p.parse_args(argv)
    if not args.repo and not args.site:
        p.error("give --repo, --site, or both")
    args.jurisdictions = [j.strip().upper() for j in args.jurisdictions.split(",") if j.strip()]
    if unknown := [j for j in args.jurisdictions if j not in JURISDICTIONS]:
        p.error(f"unknown jurisdiction: {', '.join(unknown)}")
    return args


def summary(report: AuditReport) -> str:
    cell = {(c.jurisdiction, c.area): c.status for c in report.matrix}
    jurisdictions = list(dict.fromkeys(c.jurisdiction for c in report.matrix))
    lines = [f"{'':4}" + "".join(f"{a:<17}" for a in AREAS)]
    lines += [f"{j:4}" + "".join(f"{cell[(j, a)].upper():<17}" for a in AREAS) for j in jurisdictions]
    notes = dict.fromkeys(c.headline for c in report.matrix if c.status == "grey" and c.area != "financial")
    lines += [f"GREY = {note}" for note in notes] + [""]
    for f in report.findings:
        where = ", ".join(f"{j} {s}" for j, s in finding_status_by_jurisdiction(report, f.id).items())
        lines.append(f"{f.id:3} [{where}] {f.title}")
    if not report.findings:
        lines.append("No possible inconsistencies found.")
    return "\n".join(lines)


def exit_code(report: AuditReport, events: list[ProgressEvent], fail_on: str) -> int:
    worst = max((RANK[c.status] for c in report.matrix), default=0)
    if fail_on != "never" and worst >= RANK[fail_on]:
        return EXIT_FAILED_GATE
    # A step that failed means the result is not a clean pass, whatever the matrix says.
    return EXIT_INCOMPLETE if any(e.status == "error" for e in events) else 0


def main(argv: list[str] | None = None) -> int:
    args = _args(argv)
    events: list[ProgressEvent] = []

    def emit(event: ProgressEvent) -> None:
        events.append(event)
        if event.status != "running":
            print(f"{event.step:13s} {event.status:8s} {event.message}", file=sys.stderr)

    req = AuditRequest(repo_url=args.repo, site_url=args.site, policy_url=args.policy, jurisdictions=args.jurisdictions,
                       effort=args.effort)  # fmt: skip
    report = asyncio.run(run_audit("cli", req, emit, use_llm=not args.no_llm))
    if args.markdown:
        args.markdown.write_text(render(report))
    if args.json:
        args.json.write_text(report.model_dump_json(indent=2) + "\n")
    print(summary(report), flush=True)
    code = exit_code(report, events, args.fail_on)
    if code == EXIT_FAILED_GATE:
        print(f"\nFailed: at least one cell is {args.fail_on} or worse (--fail-on {args.fail_on}).", file=sys.stderr)
    elif code == EXIT_INCOMPLETE:
        print("\nIncomplete: a step failed, so this is not a clean result.", file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
