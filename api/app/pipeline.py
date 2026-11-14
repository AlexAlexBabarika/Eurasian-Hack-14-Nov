"""Orchestrates the audit steps and emits progress events. A failed step emits status=error and the audit continues."""

import time
from collections.abc import Callable

from app import llm
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
    Finding,
    Observation,
    PolicyClaims,
    ProgressEvent,
    Step,
)
from app.verdict.engine import Matrix, build_matrix

Emit = Callable[[ProgressEvent], None]

EMPTY_CLAIMS = PolicyClaims(
    data_categories=[], named_processors=[], sharing_statement="unclear", mentions_ai=False,
    international_transfers=False, retention_stated=False, rights_listed=[], deletion_method=None,
    cookie_consent_described=False, quotes={},
)  # fmt: skip


def _passes(passes: list[tuple[str, site.ConsentPass]], net_obs: list[Observation], stats: dict) -> str:
    """Per-pass stats and the tail of the site_scan message. Empty for a scan that only ran the first pass."""
    if not passes:
        return ""
    still = [o.vendor for o in net_obs if trackers.seen(o, trackers.AFTER_REJECT) and trackers.is_tracker(o)]
    gated = [o.vendor for o in net_obs if trackers.gated(o)]
    stats["site_passes"] = {}
    out = []
    for name, p in passes:
        failed = f"failed ({p.error[:80]})" if p.error else "no banner found"
        stats["site_passes"][name] = f"clicked: {p.clicked}" if p.clicked else failed
        if not p.clicked:
            out.append(f"{name}: {failed}")
            continue
        stats[f"requests_after_{name}"] = len(p.requests)
        if name == "reject":
            stats["trackers_after_reject"] = still
            verb = "still fires" if len(still) == 1 else "still fire"
            out.append(f"after reject: {', '.join(still)} {verb}" if still else "after reject: no trackers")
        else:
            stats["vendors_after_accept_only"] = gated
            more = f"{len(gated)} more vendor{'s' if len(gated) != 1 else ''}"
            out.append(f"after accept: {more} ({', '.join(gated)})" if gated else "after accept: no more vendors")
    return "; " + "; ".join(out)


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
        ev("site_scan", "running", "Loading the site in clean browsers: clicking nothing, rejecting, accepting")
        scan = await site.scan(req.site_url)
    else:
        scan = site.SiteScan(url="")
    net_obs = trackers.detect(scan)
    stats["requests_pre_consent"] = len(scan.requests)
    passes = [(name, p) for name in ("reject", "accept") if (p := getattr(scan, name))]
    if not req.site_url:
        ev("site_scan", "skipped", "No live site given; only the code is compared with the policy")
    elif scan.error and not scan.requests and not any(p.clicked for _, p in passes):
        ev("site_scan", "error", f"Site scan failed: {scan.error[:160]}")
    else:
        names = ", ".join(o.vendor or "" for o in net_obs if o.pre_consent) or "none"
        message = f"{len(scan.requests)} requests before consent; trackers: {names}"
        ev("site_scan", "done", message + _passes(passes, net_obs, stats), len(net_obs))
    observations = trackers.merge(code_obs, net_obs)
    stats["vendors_found"] = len([o for o in observations if o.vendor])

    # policy
    policy_text = ""
    if req.policy_url:
        ev("policy_fetch", "running", "Fetching the privacy policy")
        try:
            policy_text = await policy.fetch(req.policy_url)
            linked = policy_text.count(policy.LINKED_PAGE)
            extra = f", including {linked} linked subprocessor page{'s' if linked > 1 else ''}" if linked else ""
            ev("policy_fetch", "done", f"Policy text extracted ({len(policy_text):,} characters{extra})", len(policy_text))
        except Exception as e:  # noqa: BLE001
            ev("policy_fetch", "error", f"Could not fetch policy: {str(e)[:160]}")
    else:
        ev("policy_fetch", "skipped", "No privacy policy given; only the checks that need no policy run")

    # claims
    claims = EMPTY_CLAIMS
    failed: list[str] = []  # steps that raised: their areas must read "not assessed", never green
    model = llm.model_for(req.effort)
    stats["effort"] = req.effort
    if policy_text:
        ev("claims", "running", "Extracting what the policy claims")
        try:
            if use_llm:
                claims, method = await claims_extract.extract(policy_text, model)
            else:
                claims, method = claims_extract.validate_quotes(claims_extract.heuristic(policy_text), policy_text), "heuristic"
            stats["claims_method"] = method
            ev("claims", "done", f"Claims extracted ({method}); sharing statement: {claims.sharing_statement}")
        except Exception as e:  # noqa: BLE001
            failed.append("the policy claims could not be extracted")
            ev("claims", "error", f"Claims extraction failed: {str(e)[:160]}")
        ev("diff", "running", "Comparing observed behaviour with policy claims")
    else:
        ev("claims", "skipped", "No policy text, so nothing to compare against")
        ev("diff", "running", "Running the checks that need no policy text")
    # diff: without policy text only the rules that need none (consent, logs) can be evidenced
    findings: list[Finding] = []
    try:
        findings = run_rules(observations, claims, signals, req.policy_url if policy_text and not failed else None, len(files))
        ev("diff", "done", f"{len(findings)} possible inconsistencies", len(findings))
    except Exception as e:  # noqa: BLE001
        failed.append("the checks could not be run")
        ev("diff", "error", f"Rule engine failed: {str(e)[:160]}")

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
        gaps.append("the policy could not be read" if req.policy_url else "no privacy policy was given")
    gaps += failed
    failure = ""
    try:
        built = await build_matrix(
            findings, observations, jurisdictions, use_llm=use_llm, gaps=gaps,
            on_cell=lambda n, total: ev("verdict", "running", f"Writing verdicts: {n} of {total} cells", n), model=model,
        )
    except Exception as e:  # noqa: BLE001
        failure = str(e)[:160]
        try:
            built = await build_matrix(findings, observations, jurisdictions, use_llm=False, gaps=gaps)
        except Exception as e2:  # noqa: BLE001
            failure = str(e2)[:160]
            built = Matrix([], {}, "error")
    matrix, provisions, method, llm_cells, fallbacks = built
    stats["verdict_method"] = method
    if method == "llm":
        stats["verdict_fallbacks"] = fallbacks
    fell_back = f"; {fallbacks} of {llm_cells} LLM cells fell back to template text" if fallbacks else ""
    if method == "error":
        ev("law", "error", f"No provisions retrieved: {failure}")
        ev("verdict", "error", f"Could not write verdicts: {failure}")
    else:
        ev("law", "done", f"{len(provisions)} provisions cited", len(provisions))
        if failure:
            ev("verdict", "error", f"Verdict step failed once, so all cells use template text: {failure}", len(matrix))
        else:
            ev("verdict", "done", f"{len(matrix)} matrix cells ({method}{fell_back})", len(matrix))

    stats["duration_s"] = round(time.monotonic() - t0, 1)
    report = AuditReport(
        id=audit_id, inputs=req.model_dump(), observations=observations, claims=claims, findings=findings,
        matrix=matrix, provisions=provisions, stats=stats, disclaimer=DISCLAIMER,
    )  # fmt: skip
    ev("done", "done", f"Audit finished in {stats['duration_s']}s")
    return report
