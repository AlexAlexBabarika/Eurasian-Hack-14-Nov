- Contracts live in api/app/models.py. Do not change field names without updating contracts/sample_report.json and running `make types`.
- Every Finding must have ≥1 Evidence. Every CellVerdict.provision_ids entry must exist in law/corpus. Enforce in code, not only in prompts.
- Never write "violates" or "illegal" in generated text; use "possible inconsistency with".
- Timeouts everywhere: clone 30s, Bearer 90s, Playwright 15s, LLM 60s. A failed step emits an SSE event with status=error and the pipeline continues.
- Python: uv, ruff, type hints, Pydantic v2. JS: pnpm, strict TS, shadcn/ui components, no new UI libraries.
- Keep files small; one module per responsibility as in PLAN.md §3. Do not add databases, queues, or auth.
- Tests: `make test` must pass before merging to main.

## Commands
- `make setup` installs everything (uv sync, Playwright Chromium, pnpm install).
- `make api` runs FastAPI on :8000, `make web` runs Next.js on :3000, `make dev` runs both.
- `make test` runs ruff + pytest (api) and tsc + eslint (web). Tests need no API key or network.
- `make types` regenerates web/src/lib/api-types.ts from the FastAPI OpenAPI schema.
- `make sample` regenerates contracts/sample_report.json from demo/fixture-app (offline, no LLM).
- Without ANTHROPIC_API_KEY the claims and verdict steps fall back to deterministic heuristics, so the pipeline still runs end-to-end.
