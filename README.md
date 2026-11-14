# Groundtruth

Privacy policy vs. code auditor. Give it a GitHub repo, a live site URL and a privacy policy URL; it finds what the product actually collects and sends, compares that with what the policy claims, and maps each possible inconsistency to official law in the UK, EU and Kazakhstan.

Not legal advice. Every finding carries evidence; every legal reference comes from the curated corpus in `api/app/law/corpus/`.

Full plan: [PLAN.md](PLAN.md). Rules for coding agents: [AGENTS.md](AGENTS.md).

## Quick start

Requires `uv`, `pnpm` and Node 20+.

```sh
cp .env.example .env      # add LLM_API_KEY (optional, see below)
make setup                # uv sync, Playwright Chromium, pnpm install
make dev                  # API on :8000, web on :3000
```

Try it on the built-in demo product:

```sh
make fixture              # serves demo/fixture-app on :4100
```

Then open http://localhost:3000 and click "Use demo fixture".

Without `LLM_API_KEY` the pipeline still runs end to end: policy claims come from keyword heuristics and verdict text from templates. With a key, the model extracts the claims and writes the verdict prose and fixes. Cell statuses are decided by deterministic rules either way.

### Docker

```sh
cp .env.example .env      # required: docker-compose.yml reads it via env_file
docker compose up api     # API on :8000 with Chromium, git and Bearer; run the web app with `make web`
```

Inside the container `localhost` is the container itself. To audit something served on your machine (for example `make fixture`), use `http://host.docker.internal:4100/...` as the site and policy URLs.

### MCP server

`mcp/server.py` exposes the audit as one tool, `audit_product(repo_url, site_url, policy_url, jurisdictions)`, over stdio and returns the Markdown report. `jurisdictions` is optional: a list of `UK`, `EU`, `KZ` that limits the matrix and verdicts; leave it out for all three. Needs `mcp` 2.x (installed by `make setup`).

```sh
uv run --project api python mcp/server.py
```

To use it from Claude Code, Cursor or Claude Desktop, see [mcp/README.md](mcp/README.md). The repo ships `.mcp.json` and `.cursor/mcp.json`, so the first two need no configuration.

With `DEMO_MODE=cached` (in `.env` or the server's environment), inputs that match a saved audit in `api/data/audits/` return that report at once, without cloning or scanning. Other inputs still run a live audit.

### LLM provider

`api/app/llm.py` talks to any OpenAI-compatible chat-completions API. Set `LLM_API_KEY`, `LLM_BASE_URL` (default: OpenRouter) and `MODEL_FAST` in `.env`. The model must support forced tool calls; if a call fails twice, that step falls back to the heuristic or template output. If only `ANTHROPIC_API_KEY` is set, Anthropic's OpenAI-compatible endpoint is used.

## Commands

| Command | What it does |
|---|---|
| `make test` | ruff + pytest (api), tsc + eslint (web). No network or API key needed. |
| `make types` | Regenerate `web/src/lib/api-types.ts` from the FastAPI schema. |
| `make sample` | Regenerate `contracts/sample_report.json` and the cached demo audit. |
| `make demo` | Run with `DEMO_MODE=cached`: matching inputs replay a cached audit. |
| `docker compose up api` | API in a container with Chromium, git and Bearer. |

## How it works

1. **Ingest**: shallow clone, Playwright site load with no clicks (requests and cookies before consent), policy text via trafilatura.
2. **Detect**: dependency manifests and imports matched against `sdk_catalog.yaml` (30 vendors), optional Bearer CLI scan, grep signals for delete-account routes and personal data in logs.
3. **Claims**: policy text to `PolicyClaims`; quotes must be exact substrings of the policy.
4. **Diff**: deterministic rules R1-R9 produce findings.
5. **Law**: tag filter + BM25 over the curated corpus.
6. **Verdict**: a 3 x 4 matrix (jurisdiction x legal area) with reasoning, citations and paste-ready fixes.

## Status of the law corpus

All provisions currently have `verified: false`. A human must open each `official_url`, confirm the reference and summary, and only then set `verified: true`.
