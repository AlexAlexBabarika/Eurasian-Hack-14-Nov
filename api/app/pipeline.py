"""Orchestrates the audit steps and emits progress events. A failed step emits status=error and the audit continues."""

import time
from collections.abc import Callable

from app.claims import extract as claims_extract
from app.detect import bearer, code_signals, manifests, trackers
from app.detect.code_signals import CodeSignals
from app.diff.rules import run_rules
from app.ingest import policy, repo, site
from app.ingest.repo import RepoFile
from app.models import (
    DISCLAIMER,
    JURISDICTIONS,
    AuditReport,
    AuditRequest,
    Observation,
    PolicyClaims,
    ProgressEvent,
    Step,
)
from app.verdict.engine import build_matrix

Emit = Callable[[ProgressEvent], None]

EMPTY_CLAIMS = PolicyClaims(
    data_categories=[], named_processors=[], sharing_statement="unclear", mentions_ai=False,
    international_transfers=False, retention_stated=False, rights_listed=[], deletion_method=None,
    cookie_consent_described=False, quotes={},
)  # fmt: skip


async def run_audit(audit_id: str, req: AuditRequest, emit: Emit, use_llm: bool = True) -> AuditReport:
    t0 = time.monotonic()
    stats: dict = {}

    def ev(step: Step, status: str, message: str, count: int | None = None) -> None:
        emit(ProgressEvent(step=step, status=status, message=message, count=count))

    # clone
    files: list[RepoFile] = []
    repo_dir = None
    if req.repo_url:
        ev("clone", "running", "Fetching repository")
        try:
            repo_dir = await repo.fetch(req.repo_url)
            files, total = repo.walk(repo_dir)
            stats["files_total"] = total
            capped = f" of {total:,} (file cap; manifests and source files first)" if total > repo.MAX_FILES else ""
            ev("clone", "done", f"{len(files):,} files ready to scan{capped}", len(files))
        except Exception as e:  # noqa: BLE001
            ev("clone", "error", f"Could not fetch repository: {str(e)[:160]}")
    else:
        ev("clone", "skipped", "No repository given; only the live site is compared with the policy")
    stats["files_scanned"] = len(files)

    # manifests + SDK catalog + code signals
    code_obs: list[Observation] = []
    signals = CodeSignals()
    if req.repo_url:
        ev("manifests", "running", "Matching dependencies and imports against the SDK catalog")
        try:
            code_obs = manifests.detect(files)
            signals = code_signals.detect(files)
            names = ", ".join(o.vendor or "" for o in code_obs) or "none"
            ev("manifests", "done", f"Vendors in code: {names}", len(code_obs))
        except Exception as e:  # noqa: BLE001
            ev("manifests", "error", f"Manifest detector failed: {str(e)[:160]}")
    else:
        ev("manifests", "skipped", "No repository to read dependencies from")

    # bearer (optional)
    if req.repo_url:
        ev("bearer", "running", "Running Bearer data-flow scan")
    result = await bearer.run(repo_dir) if repo_dir else bearer.BearerResult(message="No repository to scan")
    stats["bearer"] = result.ran
    signals.pii_logs.extend(result.pii_logs)
    for cat, evidence in result.data_types.items():
        code_obs.append(Observation(
            id=f"bearer-{cat}", vendor=None, vendor_country=None, data_categories=[cat], purpose_guess=None,
            evidence=evidence[:4],
        ))  # fmt: skip
    ev("bearer", "done" if result.ran else "skipped", result.message, len(result.data_types) if result.ran else None)

    # site scan
    if req.site_url:
        ev("site_scan", "running", "Loading the site in a clean browser, clicking nothing")
        scan = await site.scan(req.site_url)
    else:
        scan = site.SiteScan(url="")
    net_obs = trackers.detect(scan)
    stats["requests_pre_consent"] = len(scan.requests)
    if not req.site_url:
        ev("site_scan", "skipped", "No live site given; only the code is compared with the policy")
    elif scan.error and not scan.requests:
        ev("site_scan", "error", f"Site scan failed: {scan.error[:160]}")
    else:
        names = ", ".join(o.vendor or "" for o in net_obs) or "none"
        ev("site_scan", "done", f"{len(scan.requests)} requests before consent; trackers: {names}", len(net_obs))
    observations = trackers.merge(code_obs, net_obs)
    stats["vendors_found"] = len([o for o in observations if o.vendor])

    # policy
    ev("policy_fetch", "running", "Fetching the privacy policy")
    policy_text = ""
    try:
        policy_text = await policy.fetch(req.policy_url)
        linked = policy_text.count(policy.LINKED_PAGE)
        extra = f", including {linked} linked subprocessor page{'s' if linked > 1 else ''}" if linked else ""
        ev("policy_fetch", "done", f"Policy text extracted ({len(policy_text):,} characters{extra})", len(policy_text))
    except Exception as e:  # noqa: BLE001
        ev("policy_fetch", "error", f"Could not fetch policy: {str(e)[:160]}")

    # claims
    findings = []
    claims = EMPTY_CLAIMS
    if policy_text:
        ev("claims", "running", "Extracting what the policy claims")
        if use_llm:
            claims, method = await claims_extract.extract(policy_text)
        else:
            claims, method = claims_extract.validate_quotes(claims_extract.heuristic(policy_text), policy_text), "heuristic"
        stats["claims_method"] = method
        ev("claims", "done", f"Claims extracted ({method}); sharing statement: {claims.sharing_statement}")

        # diff: only meaningful when we have a policy to compare against
        ev("diff", "running", "Comparing observed behaviour with policy claims")
        findings = run_rules(observations, claims, signals, req.policy_url, len(files))
        ev("diff", "done", f"{len(findings)} possible inconsistencies", len(findings))
    else:
        ev("claims", "skipped", "No policy text, so nothing to compare against")
        ev("diff", "skipped", "No policy text; no findings can be evidenced")

    # law + verdict
    jurisdictions = req.jurisdictions or JURISDICTIONS
    ev("law", "running", "Retrieving provisions from the curated corpus")
    ev("verdict", "running", "Writing verdicts per jurisdiction")
    gaps = []
    if not req.repo_url:
        gaps.append("no repository was given")
    elif not files:
        gaps.append("the repository could not be read")
    if not req.site_url:
        gaps.append("no live site was given")
    if not policy_text:
        gaps.append("the policy could not be read")
    matrix, provisions, method = await build_matrix(
        findings, observations, jurisdictions, use_llm=use_llm, gaps=gaps,
        on_cell=lambda n, total: ev("verdict", "running", f"Writing verdicts: {n} of {total} cells", n),
    )
    stats["verdict_method"] = method
    ev("law", "done", f"{len(provisions)} provisions cited", len(provisions))
    ev("verdict", "done", f"{len(matrix)} matrix cells ({method})", len(matrix))

    stats["duration_s"] = round(time.monotonic() - t0, 1)
    report = AuditReport(
        id=audit_id, inputs=req.model_dump(), observations=observations, claims=claims, findings=findings,
        matrix=matrix, provisions=provisions, stats=stats, disclaimer=DISCLAIMER,
    )  # fmt: skip
    ev("done", "done", f"Audit finished in {stats['duration_s']}s")
    return report
