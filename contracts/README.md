# Contracts

Source of truth: `api/app/models.py` (Pydantic). `sample_report.json` is a full, realistic `AuditReport` generated from `demo/fixture-app` by `make sample`; the web UI can be built against it without a running backend.

Changing a field: edit `models.py`, run `make sample` and `make types`, then tell the team.

## Field notes

- `observations[]`: what the product does. One per vendor, merged from code and network evidence. `pre_consent` is true when the vendor was seen on the site before any consent click. `vendor: null` means first-party processing found by Bearer.
- `inputs`: the request as sent. `policy_url` is null when no policy was given; then `claims` is empty and only R5, R8 and R10 can produce findings.
- `claims`: what the policy says. Every entry in `claims.quotes` is an exact substring of the policy text (enforced in code).
- `findings[]`: output of rules R1-R9. `evidence` is never empty. Findings are jurisdiction-neutral.
- `matrix[]`: one `CellVerdict` per jurisdiction x area (3 x 4). `financial` is always `grey`.
  - `status`: worst status among the cell's findings, after caps (UK `ai_transparency` is at most `amber`).
  - `finding_statuses`: finding id -> status of that finding in this jurisdiction. This is how the same evidence shows as amber in UK and red in EU (R5, cookies). Addition to the PLAN.md §4 contract.
  - `provision_ids`: all exist in `provisions` and in `api/app/law/corpus/`.
  - `unverified_notes`: reasons to show a warning on the cell (unverified provisions, dropped citations).
- `provisions`: only the provisions cited by the matrix, keyed by id. `verified: false` must render with a warning.
- `stats`: `files_scanned`, `vendors_found`, `requests_pre_consent`, `duration_s`, plus `bearer` (did it run), `claims_method` (`llm` | `heuristic`), `verdict_method` (`llm` | `deterministic`), `effort` (`fast` | `strong`: which model the request asked for).

## SSE events (`GET /audits/{id}/events`)

`event: progress`, data `{step, status, message, count?}`. Steps in order: `clone`, `manifests`, `bearer`, `site_scan`, `policy_fetch`, `claims`, `diff`, `law`, `verdict`, `done`. Status: `running` | `done` | `error` | `skipped`. The stream closes with `event: end`.
