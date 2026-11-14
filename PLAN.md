# Groundtruth: Privacy Policy vs. Code Auditor
Hackathon build plan for a team of 3 (A, B, C) in about 7 hours.
Paste this whole file into Devin or Claude Code as the project brief, and keep it at the repo root as `PLAN.md`.

---

## 0. One-paragraph pitch
Startups write privacy policies from templates. Then the code ships Mixpanel, Sentry, OpenAI and Google Analytics, and the policy never catches up. Groundtruth takes a **GitHub repo + live site URL + privacy policy URL**. It finds what the product **actually** collects and sends (code + network evidence), compares that with what the policy **claims**, and maps every contradiction to the official law in **UK, EU and Kazakhstan**. The output is a **3×3 traffic-light matrix** (jurisdiction × legal area). Every cell has evidence (file:line, policy quote, network request), a link to the official legal text and a ready-to-paste fix.

Positioning: "Website GDPR scanners read your policy. Enterprise code scanners cost five figures. We do both, for a startup, in 2 minutes, across UK/EU/KZ."

## 1. Scope (hard limits; do not expand during the hackathon)
**Jurisdictions:** UK, EU, KZ (Kazakhstan).
**Legal areas (matrix columns):**
1. Personal data (UK GDPR + DPA 2018 + PECR as amended by DUAA 2025 / EU GDPR + ePrivacy / KZ Law on Personal Data)
2. AI transparency (EU AI Act Art. 50 / KZ Law on AI No. 230-VIII / UK: no AI statute → ICO guidance, max status AMBER)
3. Consumer protection (account deletion, dark patterns, consent UX) (UK DMCC Act 2024 Part 4 / EU UCPD / KZ consumer law)

**Out of scope:** financial licensing (shown as a GREY cell, "needs questionnaire"), US law, mobile app binaries, authenticated pages.

**Input:** `repo_url` (public GitHub), `site_url`, `policy_url`. Optional: list of jurisdictions.
**Output:** `AuditReport` JSON → web UI matrix + findings + Markdown export. Optional MCP tool `audit_product`.

**Golden rule:** no finding without evidence, no legal claim without a provision from our curated corpus. Anything else is dropped or labelled "unverified". The wording is always "possible inconsistency". This is not legal advice.

---

## 2. Tech stack (final decisions)
| Layer | Choice | Why |
|---|---|---|
| Frontend | **Next.js 15 (App Router) + TypeScript + Tailwind v4 + shadcn/ui** | fastest path to a polished UI; shadcn gives tables, sheets, badges, tabs |
| FE data | **TanStack Query** + native `EventSource` (SSE) | live progress timeline during the audit |
| Code highlighting | **shiki** | evidence snippets look professional |
| Backend | **Python 3.12 + FastAPI + Pydantic v2 + uvicorn** | best ecosystem for LLM, scraping and scanners; Pydantic = typed contracts |
| Python tooling | **uv** (deps + venv), **ruff** | install in seconds |
| JS tooling | **pnpm** | |
| LLM | **Anthropic API**: `claude-sonnet-5-5` for extraction/verdicts (fast), `claude-opus-5-5` optional for the final verdict pass | structured output via forced tool use + Pydantic validation + 1 retry |
| Code scanning | **Bearer CLI** (`bearer scan --report privacy --format json`) + our own **manifest/SDK detector** (always runs) | Bearer gives data types + third parties; our detector is the fallback if Bearer fails |
| Site scanning | **Playwright (Chromium, headless)** | record requests/cookies **before** any consent click = hard evidence |
| Policy text | **httpx + trafilatura** | clean main-text extraction from the policy page |
| Law retrieval | **Curated YAML corpus + tag filter + BM25 (`rank-bm25`)**, no vector DB | ~40 provisions, deterministic, zero infra, citations can be whitelisted |
| Streaming | **sse-starlette** | progress events to the UI |
| Storage | in-memory dict + JSON files in `./data/audits/` | no DB needed; also used for the cached demo |
| MCP (stretch) | **`mcp` Python SDK 2.x (MCPServer)** | exposes `audit_product` to Claude/Cursor |
| Types FE↔BE | FastAPI OpenAPI → **`openapi-typescript`** → `web/src/lib/api-types.ts` | one source of truth (Pydantic) |
| Run/demo | `docker compose` (api image includes Chromium + git + bearer) + local `pnpm dev` | demo runs locally; Vercel deploy of `web/` is optional |

Env vars (`.env.example`): `ANTHROPIC_API_KEY`, `MODEL_FAST=claude-sonnet-5-5`, `MODEL_STRONG=claude-opus-5-5`, `DEMO_MODE=live|cached`, `GITHUB_TOKEN` (optional, avoids rate limits).

---

## 3. Repo structure (ownership baked in)
```
groundtruth/
├── PLAN.md                     # this file
├── AGENTS.md                   # short rules for coding agents (see §11)
├── README.md
├── Makefile                    # make dev | make api | make web | make types | make demo | make test
├── docker-compose.yml
├── .env.example
│
├── contracts/                  # OWNER: all. Frozen at H0:30; changes need a 2-min team check
│   ├── sample_report.json      # realistic full AuditReport; C builds UI on this from minute 30
│   └── README.md               # field meanings
│
├── api/                        # Python. Run: uv run uvicorn app.main:app --reload
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py             # FastAPI app, routes, SSE                    (C, H0.5–1.5)
│   │   ├── models.py           # Pydantic contracts (§4)                     (ALL, H0–0.5)
│   │   ├── pipeline.py         # orchestrates the steps, emits events        (A)
│   │   ├── llm.py              # Anthropic client, structured calls, retry   (B)
│   │   ├── ingest/
│   │   │   ├── repo.py         # shallow clone, file walk, size limits       (A)
│   │   │   ├── site.py         # Playwright: requests, cookies, pre-consent  (A)
│   │   │   └── policy.py       # fetch + trafilatura → clean text            (A)
│   │   ├── detect/
│   │   │   ├── manifests.py    # package.json, requirements, pyproject, go.mod, Gemfile, pubspec, build.gradle (A)
│   │   │   ├── sdk_catalog.yaml# vendor → packages, domains, data categories, country, is_ai (A)
│   │   │   ├── bearer.py       # run Bearer, parse privacy report            (A)
│   │   │   ├── code_signals.py # grep: delete-account routes, logging PII, region configs (A)
│   │   │   └── trackers.py     # network domain → vendor via catalog         (A)
│   │   ├── claims/
│   │   │   └── extract.py      # LLM: policy text → PolicyClaims             (B)
│   │   ├── diff/
│   │   │   └── rules.py        # deterministic rules R1–R9 (§6)              (A builds, B reviews)
│   │   ├── law/
│   │   │   ├── corpus/uk.yaml  # curated provisions with official URLs     (B)
│   │   │   ├── corpus/eu.yaml  #                                             (B)
│   │   │   ├── corpus/kz.yaml  #                                             (B)
│   │   │   └── retrieve.py     # tag filter + BM25                           (B)
│   │   ├── verdict/
│   │   │   ├── engine.py       # findings × provisions → CellVerdicts + fixes(B)
│   │   │   └── prompts/        # verdict.md, fix.md, claims.md               (B)
│   │   └── report/
│   │       └── markdown.py     # export report                               (C)
│   ├── data/audits/            # cached reports (gitignored except demo)
│   └── tests/
│       ├── test_rules.py       # golden tests on the demo fixture            (A)
│       └── test_citations.py   # every cited provision_id exists in corpus   (B)
│
├── web/                        # Next.js. Run: pnpm dev                       (C)
│   ├── src/app/page.tsx        # input form (3 URLs + jurisdiction toggles)
│   ├── src/app/audit/[id]/page.tsx  # progress timeline → matrix → findings
│   ├── src/components/Matrix.tsx, FindingCard.tsx, EvidenceBlock.tsx, LawCitation.tsx, FixDiff.tsx, ProgressTimeline.tsx
│   └── src/lib/api.ts, api-types.ts (generated)
│
├── mcp/
│   └── server.py               # MCPServer: audit_product(repo_url, site_url, policy_url) (C, stretch)
│
└── demo/
    ├── fixture-app/            # deliberately non-compliant mini product (A+C, H0.5–1.5)
    │   ├── package.json        # mixpanel-browser, @sentry/nextjs, openai, stripe, posthog-js
    │   ├── src/...             # sends email+name to Mixpanel, user chat text to OpenAI, logs email
    │   ├── public/index.html   # loads GA/PostHog BEFORE consent
    │   └── privacy.html        # claims "we never share your data with third parties", no AI mention, no retention period
    └── SCRIPT.md               # 3-minute demo script (§9)
```
Branches: `a/detect`, `b/law-verdict`, `c/web`. Merge to `main` at H4 and H5.5 only (plus tiny fixes). Everyone runs `make test` before merging.

---

## 4. Data contracts (Pydantic, `api/app/models.py`): write these FIRST (H0–0.5, all three together)
```python
from enum import Enum
from pydantic import BaseModel, HttpUrl
from typing import Literal

Jurisdiction = Literal["UK", "EU", "KZ"]
Area = Literal["personal_data", "ai_transparency", "consumer", "financial"]
Status = Literal["red", "amber", "green", "grey"]

class Evidence(BaseModel):
    kind: Literal["code", "manifest", "network", "cookie", "policy_quote", "bearer"]
    summary: str                 # "posthog-js loaded before consent"
    file: str | None = None      # "src/lib/analytics.ts"
    line: int | None = None
    snippet: str | None = None   # max ~12 lines
    url: str | None = None       # network request URL or policy URL
    quote: str | None = None     # exact policy sentence

class Observation(BaseModel):    # what the product DOES
    id: str
    vendor: str | None           # "Mixpanel"
    vendor_country: str | None   # "US"
    data_categories: list[str]   # ["email","name","usage","device_id","ip","user_content","payment","location","health"]
    purpose_guess: str | None    # "analytics" | "error_monitoring" | "ai_processing" | "payments" | "ads"
    is_ai: bool = False
    pre_consent: bool = False    # fired before consent on site
    evidence: list[Evidence]

class PolicyClaims(BaseModel):   # what the policy SAYS
    data_categories: list[str]
    named_processors: list[str]
    sharing_statement: Literal["no_sharing", "processors_only", "sells_or_shares", "unclear"]
    mentions_ai: bool
    international_transfers: bool
    retention_stated: bool
    rights_listed: list[str]     # ["access","erasure","objection","portability"]
    deletion_method: str | None
    cookie_consent_described: bool
    quotes: dict[str, str]       # key → exact sentence used as evidence

class Finding(BaseModel):
    id: str
    rule: str                    # "R1_UNDISCLOSED_PROCESSOR"
    title: str                   # "Mixpanel receives email, policy names no processors"
    severity: Literal["high", "medium", "low"]
    areas: list[Area]
    observation_ids: list[str]
    evidence: list[Evidence]     # MUST be non-empty (validated)
    policy_quote: str | None

class Provision(BaseModel):
    id: str                      # "EU-GDPR-13-1-e"
    jurisdiction: Jurisdiction
    area: Area
    instrument: str              # "Regulation (EU) 2016/679 (GDPR)"
    ref: str                     # "Art. 13(1)(e)"
    title: str
    summary: str                 # 1–3 sentences, our paraphrase
    official_url: HttpUrl
    tags: list[str]              # ["processors","recipients","transparency"]
    verified: bool               # set True only after a human checked the URL + ref

class Fix(BaseModel):
    policy_clause: str | None    # paste-ready text
    code_change: str | None      # short diff or instruction

class CellVerdict(BaseModel):
    jurisdiction: Jurisdiction
    area: Area
    status: Status
    headline: str
    reasoning: str
    finding_ids: list[str]
    provision_ids: list[str]     # MUST all exist in corpus, else dropped + status note
    fixes: list[Fix]
    unverified_notes: list[str] = []

class AuditReport(BaseModel):
    id: str
    inputs: dict
    observations: list[Observation]
    claims: PolicyClaims
    findings: list[Finding]
    matrix: list[CellVerdict]    # 3 jurisdictions × 4 areas (financial = grey)
    provisions: dict[str, Provision]
    stats: dict                  # files_scanned, vendors_found, requests_pre_consent, duration_s
    disclaimer: str
```
Then: `make types` → generates `web/src/lib/api-types.ts`. C writes `contracts/sample_report.json` by hand (realistic, about 6 findings) so the UI never waits for the backend.

---

## 5. API
- `POST /audits` body `{repo_url, site_url, policy_url, jurisdictions?}` → `{id}`; starts a background task.
- `GET /audits/{id}` → `{status: "running"|"done"|"error", report?: AuditReport}`
- `GET /audits/{id}/events` (SSE) → events `{step, status, message, count?}` with steps: `clone`, `manifests`, `bearer`, `site_scan`, `policy_fetch`, `claims`, `diff`, `law`, `verdict`, `done`.
- `GET /audits/{id}/report.md` → Markdown export.
- `DEMO_MODE=cached`: if inputs match a cached audit in `data/audits/`, replay its events with realistic delays (the Wi-Fi-proof demo).

---

## 6. Pipeline + deterministic diff rules
**Pipeline (`pipeline.py`):** clone (depth 1, skip >5MB files, max 3,000 files) → manifests + SDK catalog → Bearer (timeout 90s; on failure continue) → code_signals → site scan (Playwright, 15s, no clicks; record requests, Set-Cookie, `document.cookie`) → policy fetch → claims extraction (LLM) → diff rules → law retrieval → verdicts (LLM) → report.

**SDK catalog (`sdk_catalog.yaml`), seed ~30 vendors:** Google Analytics/gtag, GTM, Meta Pixel, Mixpanel, Amplitude, Segment, PostHog, Hotjar, Microsoft Clarity, Sentry, Datadog RUM, LogRocket, FullStory, Intercom, Crisp, HubSpot, Stripe, PayPal, Firebase/Google Analytics for Firebase, Supabase, Auth0, Clerk, OpenAI, Anthropic, Google GenAI, Mistral, Cohere, Replicate, AWS SDK, Vercel Analytics. Fields: `packages` (npm/pypi/etc), `domains`, `categories`, `purpose`, `country`, `is_ai`.

**Rules (`diff/rules.py`), each produces a Finding with evidence:**
| Rule | Trigger | Areas |
|---|---|---|
| R1 UNDISCLOSED_PROCESSOR | vendor observed in code/network, not in `named_processors` and policy gives no category of recipients | personal_data |
| R2 SHARING_CONTRADICTION | `sharing_statement == "no_sharing"` but any third-party vendor receives personal data | personal_data, consumer |
| R3 UNDISCLOSED_DATA_CATEGORY | observed category (email, location, user_content…) not in `claims.data_categories` | personal_data |
| R4 AI_PROCESSING_UNDISCLOSED | `is_ai` vendor receives `user_content` and `mentions_ai == False` | ai_transparency, personal_data |
| R5 TRACKING_BEFORE_CONSENT | non-essential tracker request/cookie with `pre_consent == True` | personal_data, consumer |
| R6 TRANSFER_UNDISCLOSED | vendor_country outside jurisdiction and `international_transfers == False` | personal_data |
| R7 NO_DELETION_PATH | no erasure right/method in policy AND no delete-account route found in code | personal_data, consumer |
| R8 PII_IN_LOGS | Bearer/code_signals: email/phone logged | personal_data |
| R9 NO_RETENTION_PERIOD | `retention_stated == False` | personal_data |

Jurisdiction nuance that must show in the demo: **R5 for analytics-only cookies is RED in EU** (ePrivacy Art. 5(3) consent) **but can be AMBER in UK**, because DUAA 2025 relaxed consent for certain statistical cookies (conditions apply; B confirms wording). Same evidence, different verdict per country: that's the "this isn't a chat wrapper" moment.

---

## 7. Law corpus (`law/corpus/*.yaml`): B owns; ~12–15 provisions per jurisdiction
Format:
```yaml
- id: EU-GDPR-13-1-e
  jurisdiction: EU
  area: personal_data
  instrument: "Regulation (EU) 2016/679 (GDPR)"
  ref: "Art. 13(1)(e)"
  title: "Recipients must be disclosed"
  summary: "When collecting data, the controller must tell the person the recipients or categories of recipients."
  official_url: "https://eur-lex.europa.eu/eli/reg/2016/679/oj"
  tags: [processors, recipients, transparency]
  verified: false
```
**Seed list (B must open every URL and confirm the article before setting `verified: true`; unverified provisions render with a ⚠ badge):**
- **EU:** GDPR Art. 5(1)(a),(f); 6; 7; 13(1)(c),(e),(f); 13(2)(a) retention; 17 erasure; 22 automated decisions; 28 processors; 44 transfers → `eur-lex.europa.eu/eli/reg/2016/679/oj`. ePrivacy Dir. 2002/58/EC Art. 5(3) → `eur-lex.europa.eu/eli/dir/2002/58/oj`. AI Act Art. 50 → `eur-lex.europa.eu/eli/reg/2024/1689/oj`. UCPD 2005/29/EC → `eur-lex.europa.eu/eli/dir/2005/29/oj`.
- **UK:** UK GDPR (same article numbers as above) → `legislation.gov.uk/eur/2016/679/contents`. DPA 2018 → `legislation.gov.uk/ukpga/2018/12/contents`. PECR reg. 6 (cookies) as amended by the Data (Use and Access) Act 2025 → `legislation.gov.uk/uksi/2003/2426/contents` (+ find the DUAA 2025 page on legislation.gov.uk). DMCC Act 2024 Part 4 (unfair commercial practices) → find on legislation.gov.uk. UK AI: no statute → ICO "Guidance on AI and data protection" (ico.org.uk) as `area: ai_transparency`, cap status at AMBER.
- **KZ (adilet.zan.kz):** Law "On Personal Data and Their Protection" (No. 94-V, 21 May 2013): consent, purpose, **storage/localisation of databases in KZ** (confirm exact article), cross-border transfer. Law "On Artificial Intelligence" No. 230-VIII (signed 17 Nov 2025, in force 18 Jan 2026): transparency/user-notification articles. Consumer protection law: information duties. Use the Russian/English text on adilet; store the official URL.

Retrieval (`retrieve.py`): filter by `jurisdiction` + `area`, then BM25 over `title+summary+tags` using the finding's rule name + title. Top 3 per (finding, jurisdiction).

---

## 8. LLM prompts (B): rules that matter
- **Claims extraction:** input = policy text (truncate 40k chars). Forced tool call returning `PolicyClaims`. Every boolean that is `False` must be justified by absence; every `True` must have an exact quote in `quotes`. Validate quotes are substrings of the policy text; drop any that aren't.
- **Verdict per cell:** input = findings for that area (with evidence) + retrieved provisions (id, ref, summary) for that jurisdiction. Output `CellVerdict`. System rules:
  1. Cite **only** provision ids from the given list.
  2. Never state that a law is violated; use "possible inconsistency with".
  3. If evidence is insufficient → `grey`.
  4. `fixes.policy_clause` must be paste-ready, plain English, and name the actual vendor and data category.
- **Post-validation in code:** drop `provision_ids` not in the corpus → add to `unverified_notes`; any cell citing only unverified provisions gets a ⚠. Status AMBER cap for UK `ai_transparency`. `financial` is always grey ("needs questionnaire").
- Cache: identical inputs → reuse LLM outputs (hash key) to save time and money during rehearsals.

---

## 9. Demo (3 minutes): C owns `demo/SCRIPT.md`
1. (20s) Problem: one stat, then "every startup in this room has a template privacy policy."
2. (20s) Paste 3 URLs of `demo/fixture-app` → live progress timeline (clone → Bearer → site scan → policy → law).
3. (60s) Matrix appears. Click **EU × Personal data = RED** → "Policy says *we never share your data*; code sends email + name to Mixpanel (`src/lib/analytics.ts:14`); PostHog fires before consent" → GDPR Art. 13(1)(e) link → paste-ready fix.
4. (30s) Same cookie evidence: **UK = AMBER** (DUAA 2025 statistical-cookie relaxation), **EU = RED**. "Same code, different law. That's why this isn't a chat wrapper."
5. (30s) **KZ × AI = RED**: user chat text goes to OpenAI with no AI disclosure → KZ AI Law; plus a data-localisation note.
6. (20s) Export Markdown / show the MCP tool inside Claude: "run it in CI before every release."
Fallback: `DEMO_MODE=cached`. Also record a 60-second screen video at H6 in case everything fails.

---

## 10. Timeline + task lists with acceptance criteria
**H0:00–0:30 (all):** agree on `models.py`; C writes `contracts/sample_report.json`; repo scaffold; `.env`; everyone can run `make api` and `make web`.

### Person A: Facts engine (ingest + detect + diff)
- [ ] H0.5–1.5 `ingest/repo.py`, `detect/manifests.py`, `sdk_catalog.yaml` (30 vendors). ✅ fixture-app → detects Mixpanel, Sentry, OpenAI, Stripe, PostHog with file:line.
- [ ] H0.5–1.5 (with C) `demo/fixture-app` with planted issues (see tree).
- [ ] H1.5–2.5 `detect/bearer.py` (subprocess, JSON parse, 90s timeout, graceful skip). ✅ email/name data types with file:line on fixture.
- [ ] H2.5–3.5 `ingest/site.py` Playwright: requests + cookies before consent → `trackers.py` mapping. ✅ fixture page shows PostHog/GA `pre_consent=True`.
- [ ] H3.5–4.5 `diff/rules.py` R1–R9 + `tests/test_rules.py` golden test on fixture (expected rule ids). ✅ `make test` green.
- [ ] H4.5–5.5 `code_signals.py` (delete-account route, PII in logs), `pipeline.py` events, robustness (timeouts, big repos).

### Person B: Law + LLM (claims, corpus, verdicts)
- [ ] H0.5–1.5 `llm.py` (Anthropic client, forced tool use → Pydantic, 1 retry, response cache). `claims/extract.py`. ✅ fixture privacy.html → `sharing_statement=no_sharing`, `mentions_ai=False`, quotes are exact substrings.
- [ ] H1.5–3.5 Corpus `eu.yaml`, `uk.yaml`, `kz.yaml` (~12–15 each). Open each official URL, set `verified: true` only after checking. ✅ `tests/test_citations.py` passes; ≥80% verified.
- [ ] H3.5–4.5 `law/retrieve.py` + `verdict/engine.py` + prompts. ✅ fixture → EU×personal_data RED, UK×personal_data AMBER/RED with the cookie nuance, KZ×ai RED.
- [ ] H4.5–5.5 Fix generation quality (paste-ready clauses naming vendors), post-validation, AMBER cap for UK AI, grey for financial.

### Person C: Product (API shell, web, demo, MCP)
- [ ] H0.5–1.5 `app/main.py` routes + SSE with fake events; `make types`.
- [ ] H1–3.5 Web on `sample_report.json`: input page, `ProgressTimeline`, `Matrix` (3×4, colored, click → side Sheet), `FindingCard` with `EvidenceBlock` (shiki snippet, policy quote, network URL), `LawCitation` (ref + official link + ⚠ if unverified), `FixDiff` (copy button). Dark, sober, legal-tech look; no emojis in UI.
- [ ] H3.5–4.5 Wire to the real API; `report/markdown.py` export.
- [ ] H4.5–5.5 `DEMO_MODE=cached` replay; `mcp/server.py` (stretch); `demo/SCRIPT.md`.
- [ ] H5.5–7 Pitch deck (4 slides max), screen recording backup.

**H4:00 checkpoint (all, 20 min):** merge to `main`; fixture runs end-to-end live (ugly is fine).
**H5:30 feature freeze.** After this, only bug fixes, copy and demo polish.
**H6:00–7:00:** run the full demo 3×, cache the final audit, record the backup video, prepare Q&A answers (§12).

Cut list if behind (in order): MCP server → Bearer (keep manifest detector) → KZ consumer column → Markdown export. **Never cut:** evidence links, official citations, the UK vs EU cookie contrast.

---

## 11. `AGENTS.md` (create this file; coding agents read it)
```
- Contracts live in api/app/models.py. Do not change field names without updating contracts/sample_report.json and running `make types`.
- Every Finding must have ≥1 Evidence. Every CellVerdict.provision_ids entry must exist in law/corpus. Enforce in code, not only in prompts.
- Never write "violates" or "illegal" in generated text; use "possible inconsistency with".
- Timeouts everywhere: clone 30s, Bearer 90s, Playwright 15s, LLM 60s. A failed step emits an SSE event with status=error and the pipeline continues.
- Python: uv, ruff, type hints, Pydantic v2. JS: pnpm, strict TS, shadcn/ui components, no new UI libraries.
- Keep files small; one module per responsibility as in PLAN.md §3. Do not add databases, queues, or auth.
- Tests: `make test` must pass before merging to main.
```

---

## 12. Judge Q&A prep
- **"Isn't this just a GDPR scanner?"** No. Scanners read the policy or the site. We compare code evidence with policy claims and map them to three legal systems with official citations. Show the UK vs EU cookie cell.
- **"False positives?"** Every finding carries file:line or a network request. Wording is "possible inconsistency". Insufficient evidence = grey.
- **"Legal liability?"** First-pass engineering check for founders and their lawyers. Not legal advice; the lawyer gets a pre-built evidence pack.
- **"Why Kazakhstan?"** A new AI law (in force 18 Jan 2026) plus data-localisation rules, and nobody covers it. Our community builds there.
- **"Business model?"** Free scan → paid CI integration (block releases on new undisclosed processors) → lawyer seats. Competitors: enterprise code scanners (expensive, slow onboarding) and website-only GDPR scanners (no code evidence).
- **"What's next?"** More jurisdictions (US states), mobile app binaries, a GitHub App that comments on PRs when a new SDK appears.
