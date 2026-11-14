"""Deterministic diff rules R1–R9: observations (what the product does) vs claims (what the policy says)."""

from app.detect.catalog import vendor_by_name
from app.detect.code_signals import CodeSignals
from app.models import Area, Evidence, Finding, Observation, PolicyClaims

PERSONAL = {"email", "name", "phone", "usage", "device_id", "ip", "user_content", "payment", "location", "health"}
MAX_EVIDENCE = 8


def _names(obs: list[Observation]) -> str:
    names = [o.vendor or "Unknown vendor" for o in obs]
    if len(names) > 4:
        return ", ".join(names[:3]) + f" and {len(names) - 3} more"
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def _pick(obs: list[Observation], kinds: tuple[str, ...] = ("code", "bearer", "network", "cookie", "manifest"),
          contains: str | None = None) -> list[Evidence]:  # fmt: skip
    """Best evidence first: round-robin across vendors, preferring `kinds` order, capped."""
    per_vendor = []
    for o in obs:
        ev = [e for e in o.evidence if e.kind in kinds and (contains is None or contains in e.summary)]
        ev = ev or [e for e in o.evidence if e.kind in kinds]
        per_vendor.append(sorted(ev, key=lambda e: (kinds.index(e.kind), e.line is None)))
    out: list[Evidence] = []
    for rank in range(MAX_EVIDENCE):
        for ev in per_vendor:
            if rank < len(ev) and len(out) < MAX_EVIDENCE:
                out.append(ev[rank])
    return out


def _quote(claims: PolicyClaims, key: str, policy_url: str, summary: str) -> list[Evidence]:
    q = claims.quotes.get(key)
    return [Evidence(kind="policy_quote", summary=summary, url=policy_url, quote=q)] if q else []


def _absence(policy_url: str, summary: str) -> Evidence:
    return Evidence(kind="policy_quote", summary=summary, url=policy_url)


def _is_named(vendor: str, claims: PolicyClaims) -> bool:
    v = vendor.lower()
    return any(v in p.lower() or p.lower() in v for p in claims.named_processors)


def run_rules(observations: list[Observation], claims: PolicyClaims, signals: CodeSignals, policy_url: str,
              files_scanned: int = 0) -> list[Finding]:  # fmt: skip
    findings: list[Finding] = []

    def add(rule: str, title: str, severity: str, areas: list[Area], obs: list[Observation],
            evidence: list[Evidence], quote_key: str | None = None) -> None:  # fmt: skip
        if not evidence:
            return  # golden rule: no finding without evidence
        findings.append(Finding(
            id=f"F{len(findings) + 1}", rule=rule, title=title, severity=severity, areas=areas,
            observation_ids=[o.id for o in obs], evidence=evidence,
            policy_quote=claims.quotes.get(quote_key) if quote_key else None,
        ))  # fmt: skip

    third_party = [o for o in observations if o.vendor]
    receives_pii = [o for o in third_party if PERSONAL & set(o.data_categories)]

    # R1: vendor observed, not named, and the policy gives no category of recipients.
    undisclosed = [o for o in third_party if not _is_named(o.vendor, claims)]
    if undisclosed and claims.sharing_statement != "processors_only":
        add("R1_UNDISCLOSED_PROCESSOR",
            f"{_names(undisclosed)} observed in code or network traffic; policy names no such recipients",
            "medium", ["personal_data"], undisclosed, _pick(undisclosed))  # fmt: skip

    # R2: policy says no sharing, but third parties receive personal data.
    if claims.sharing_statement == "no_sharing" and receives_pii:
        cats = sorted({c for o in receives_pii for c in o.data_categories if c in PERSONAL})
        add("R2_SHARING_CONTRADICTION",
            f"Policy says data is not shared, but {_names(receives_pii)} receive personal data ({', '.join(cats)})",
            "high", ["personal_data", "consumer"], receives_pii,
            _quote(claims, "sharing_statement", policy_url, "Policy statement on sharing") + _pick(receives_pii)[:6],
            "sharing_statement")  # fmt: skip

    # R3: observed data category the policy does not mention.
    observed = {c for o in observations for c in o.data_categories}
    missing = sorted(observed - set(claims.data_categories))
    if missing:
        ev: list[Evidence] = []
        for cat in missing:
            holders = [o for o in observations if cat in o.data_categories]
            ev += _pick(holders, contains=cat)[:2]
        add("R3_UNDISCLOSED_DATA_CATEGORY",
            f"Data categories observed but not described in the policy: {', '.join(missing)}",
            "medium", ["personal_data"], [o for o in observations if set(missing) & set(o.data_categories)],
            ev[:MAX_EVIDENCE], "data_categories")  # fmt: skip

    # R4: AI vendor receives user content, policy does not mention AI.
    ai = [o for o in observations if o.is_ai and "user_content" in o.data_categories]
    if ai and not claims.mentions_ai:
        add("R4_AI_PROCESSING_UNDISCLOSED",
            f"User content is sent to {_names(ai)} (AI provider); policy does not mention AI processing",
            "high", ["ai_transparency", "personal_data"], ai,
            _pick(ai, contains="User-provided content") + [_absence(policy_url, "Policy text does not mention AI, "
                                                                    "machine learning or automated processing")])  # fmt: skip

    # R5: non-essential tracker fired before consent.
    trackers = [o for o in observations if o.pre_consent and not getattr(vendor_by_name(o.vendor), "essential", False)]
    if trackers:
        add("R5_TRACKING_BEFORE_CONSENT",
            f"{_names(trackers)} fire before any consent interaction on the site",
            "high", ["personal_data", "consumer"], trackers, _pick(trackers, kinds=("network", "cookie")),
            "cookie_consent_described")  # fmt: skip

    # R6: vendor based abroad, policy silent on international transfers. Per-jurisdiction filtering is in the verdict.
    abroad = [o for o in receives_pii if o.vendor_country]
    if abroad and not claims.international_transfers:
        where = sorted({o.vendor_country for o in abroad})
        add("R6_TRANSFER_UNDISCLOSED",
            f"Personal data goes to vendors based in {', '.join(where)} ({_names(abroad)}); "
            "policy does not mention international transfers",
            "medium", ["personal_data"], abroad,
            _pick(abroad)[:6] + [_absence(policy_url, "Policy text does not mention international transfers")])  # fmt: skip

    # R7: no erasure right or deletion method in the policy AND no delete-account route in code.
    if "erasure" not in claims.rights_listed and not claims.deletion_method and not signals.delete_route:
        add("R7_NO_DELETION_PATH", "No way to delete an account or data: not in the policy, no route found in code",
            "medium", ["personal_data", "consumer"], [],
            [_absence(policy_url, "Policy text lists no right to erasure and no deletion method; no delete-account "
                                  f"route found in {files_scanned} scanned files")])  # fmt: skip

    # R8: PII written to logs.
    if signals.pii_logs:
        add("R8_PII_IN_LOGS", "Personal data is written to application logs", "medium", ["personal_data"], [],
            signals.pii_logs[:MAX_EVIDENCE])  # fmt: skip

    # R9: no retention period.
    if not claims.retention_stated:
        add("R9_NO_RETENTION_PERIOD", "Policy states no retention period or criteria", "low", ["personal_data"], [],
            [_absence(policy_url, "Policy text does not state how long personal data is kept")])  # fmt: skip

    return findings
