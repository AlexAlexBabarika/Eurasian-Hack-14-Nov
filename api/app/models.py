from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, model_validator

Jurisdiction = Literal["UK", "EU", "KZ"]
Area = Literal["personal_data", "ai_transparency", "consumer", "financial"]
Status = Literal["red", "amber", "green", "grey"]

JURISDICTIONS: list[Jurisdiction] = ["UK", "EU", "KZ"]
AREAS: list[Area] = ["personal_data", "ai_transparency", "consumer", "financial"]

DISCLAIMER = (
    "Groundtruth is a first-pass engineering check. It reports possible inconsistencies between "
    "observed product behaviour and the published privacy policy. It is not legal advice."
)


class Evidence(BaseModel):
    kind: Literal["code", "manifest", "network", "cookie", "policy_quote", "bearer"]
    summary: str
    file: str | None = None
    line: int | None = None
    snippet: str | None = None
    url: str | None = None
    quote: str | None = None


class Observation(BaseModel):
    """What the product DOES."""

    id: str
    vendor: str | None
    vendor_country: str | None
    data_categories: list[str]
    purpose_guess: str | None
    is_ai: bool = False
    pre_consent: bool = False
    evidence: list[Evidence]


class PolicyClaims(BaseModel):
    """What the policy SAYS."""

    data_categories: list[str]
    named_processors: list[str]
    sharing_statement: Literal["no_sharing", "processors_only", "sells_or_shares", "unclear"]
    mentions_ai: bool
    international_transfers: bool
    retention_stated: bool
    rights_listed: list[str]
    deletion_method: str | None
    cookie_consent_described: bool
    quotes: dict[str, str]


class Finding(BaseModel):
    id: str
    rule: str
    title: str
    severity: Literal["high", "medium", "low"]
    areas: list[Area]
    observation_ids: list[str]
    evidence: list[Evidence] = Field(min_length=1)
    policy_quote: str | None


class Provision(BaseModel):
    id: str
    jurisdiction: Jurisdiction
    area: Area
    instrument: str
    ref: str
    title: str
    summary: str
    official_url: HttpUrl
    tags: list[str]
    verified: bool


class Fix(BaseModel):
    policy_clause: str | None
    code_change: str | None


class CellVerdict(BaseModel):
    jurisdiction: Jurisdiction
    area: Area
    status: Status
    headline: str
    reasoning: str
    finding_ids: list[str]
    provision_ids: list[str]
    fixes: list[Fix]
    unverified_notes: list[str] = []
    finding_statuses: dict[str, Status] = {}  # finding id → status of that finding in this jurisdiction


class AuditReport(BaseModel):
    id: str
    inputs: dict
    observations: list[Observation]
    claims: PolicyClaims
    findings: list[Finding]
    matrix: list[CellVerdict]
    provisions: dict[str, Provision]
    stats: dict
    disclaimer: str


Effort = Literal["fast", "strong"]


class AuditRequest(BaseModel):
    """repo_url or site_url may be omitted (not both): the audit then covers only what it can observe.

    Without policy_url only the checks that need no policy text run. effort picks the LLM: MODEL_FAST or MODEL_STRONG.
    """

    repo_url: str | None = None
    site_url: str | None = None
    policy_url: str | None = None
    jurisdictions: list[Jurisdiction] | None = None
    effort: Effort = "fast"

    @model_validator(mode="after")
    def _something_to_observe(self) -> "AuditRequest":
        if not self.repo_url and not self.site_url:
            raise ValueError("give a repo_url, a site_url, or both")
        return self


class AuditSummary(BaseModel):
    """One saved demo audit, for the examples list on the landing page."""

    id: str
    repo_url: str | None
    site_url: str | None
    policy_url: str | None
    findings: int
    vendors: int
    status_counts: dict[Status, int]


class AuditCreated(BaseModel):
    id: str


class AuditStatus(BaseModel):
    status: Literal["running", "done", "error"]
    report: AuditReport | None = None
    error: str | None = None


Step = Literal[
    "clone", "manifests", "bearer", "site_scan", "policy_fetch", "claims", "diff", "law", "verdict", "done"
]


class ProgressEvent(BaseModel):
    step: Step
    status: Literal["running", "done", "error", "skipped"]
    message: str
    count: int | None = None
