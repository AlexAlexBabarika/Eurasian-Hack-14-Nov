- Contracts live in api/app/models.py. Do not change field names without updating contracts/sample_report.json and running `make types`.
- Every Finding must have ≥1 Evidence. Every CellVerdict.provision_ids entry must exist in law/corpus. Enforce in code, not only in prompts.
- Never write "violates" or "illegal" in generated text; use "possible inconsistency with".
- Timeouts everywhere: clone 30s, Bearer 90s, Playwright 15s per pass (25s for the whole site scan), LLM 60s. A failed step emits an SSE event with status=error and the pipeline continues.
- Python: uv, ruff, type hints, Pydantic v2. JS: pnpm, strict TS, shadcn/ui components, no new UI libraries.
- Keep files small; one module per responsibility as in PLAN.md §3. Do not add databases, queues, or auth.
- Tests: `make test` must pass before merging to main.

## Commands
- `make setup` installs everything (uv sync, Playwright Chromium, pnpm install).
- `make api` runs FastAPI on :8000, `make web` runs Next.js on :3000, `make dev` runs both.
- `make test` runs ruff + pytest (api) and tsc + eslint (web). Tests need no API key or network.
- `make types` regenerates web/src/lib/api-types.ts from the FastAPI OpenAPI schema.
- `make sample` regenerates contracts/sample_report.json from demo/fixture-app (offline, no LLM). It also regenerates api/data/audits/demo-fixture.json and api/data/audits/demo-fixture-fixed.json (the same fixture with privacy-fixed.html).
- `make audit repo=PATH_OR_URL [policy=PATH_OR_URL] [site=URL] [effort=fast|strong] [fail_on=red|amber|never] [markdown=FILE]` runs `app.cli` (paths relative to the repo root). Exit 1 if a cell is at least `fail_on` bad, 2 if a step errored.
- LLM calls go through `api/app/llm.py` only (OpenAI-compatible API; `LLM_API_KEY`, `LLM_BASE_URL`, `MODEL_FAST`, `MODEL_STRONG`). `AuditRequest.effort` (`fast` | `strong`) picks the model. `policy_url` is optional: without policy text only R5, R8 and R10 run. Without a key the claims and verdict steps fall back to deterministic heuristics, so the pipeline still runs end-to-end.
