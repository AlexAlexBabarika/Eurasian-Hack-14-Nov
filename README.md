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

The repository field is optional: with only a site URL and a policy URL the audit compares the live site with the policy and marks what it could not see as not assessed.

For a before/after rerun, the fixture also serves the same policy with the suggested fixes pasted in: http://localhost:4100/privacy-fixed.html. Run the audit again with that policy URL; only the two findings that need code changes remain.

Without `LLM_API_KEY` the pipeline still runs end to end: policy claims come from keyword heuristics and verdict text from templates. With a key, the model extracts the claims and writes the verdict prose and fixes. Cell statuses are decided by deterministic rules either way.

### Docker

```sh
cp .env.example .env      # required: docker-compose.yml reads it via env_file
docker compose up api     # API on :8000 with Chromium, git and Bearer; run the web app with `make web`
```

Inside the container `localhost` is the container itself. To audit something served on your machine (for example `make fixture`), use `http://host.docker.internal:4100/...` as the site and policy URLs.

### MCP server

`mcp/server.py` exposes the audit as one tool, `audit_product(policy_url, repo_url, site_url, jurisdictions)`, over stdio and returns the Markdown report. `repo_url` and `site_url` are optional, but at least one is required. `jurisdictions` is optional: a list of `UK`, `EU`, `KZ` that limits the matrix and verdicts; leave it out for all three. Needs `mcp` 2.x (installed by `make setup`).

```sh
uv run --project api python mcp/server.py
```

To use it from Claude Code, Cursor or Claude Desktop, see [mcp/README.md](mcp/README.md). The repo ships `.mcp.json` and `.cursor/mcp.json`, so the first two need no configuration.

Example prompt: "Audit https://github.com/acme/app and https://acme.example against https://acme.example/privacy with the groundtruth tool, then list the findings that need a code change."

With `DEMO_MODE=cached` (in `.env` or the server's environment), inputs that match a saved audit in `api/data/audits/` return that report at once, without cloning or scanning. Other inputs still run a live audit.

If the API is reachable by other people (a public deploy, judges pasting their own URLs), set `PUBLIC_MODE=1`. Local paths are then refused, and so is any URL that points at a private or local address (`localhost`, `10.x`, cloud metadata `169.254.169.254`), including after redirects. Leave it off for the local demo, which audits `localhost:4100`.

### Run it in CI

The same audit runs from the command line and exits non-zero on a bad result. `--repo` and `--policy` take local paths or URLs; `--site` is optional and without it no browser is started.

```sh
uv run --project api python -m app.cli --repo . --policy docs/privacy.html --fail-on red --markdown report.md
make audit repo=. policy=docs/privacy.html        # same thing; paths are relative to the repo root
```

Exit codes: `0` clean, `1` at least one matrix cell is `--fail-on` (`red`, `amber`) or worse, `2` a step failed (for example the policy could not be read), so the result is incomplete. `--fail-on never` only reports. Without `--site`, cells with no findings are grey (not assessed), not green.

As a GitHub Action (the report is added to the job summary and, on pull requests, posted as a comment that later runs update in place):

```yaml
name: Privacy audit
on: pull_request
permissions:
  contents: read
  pull-requests: write   # for the report comment
jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: AlexAlexBabarika/Eurasian-Hack-14-Nov@main
        with:
          policy: docs/privacy.html
          fail-on: red
```

Other inputs: `repo` (default `.`), `site`, `jurisdictions` (default `UK,EU,KZ`), `comment` (default `true`; set `false` to keep the report in the job summary only). The comment is skipped with a warning when the token cannot write to the pull request, as on pull requests from forks. This repository runs it on its own fixture in `.github/workflows/privacy-audit.yml`.

### LLM provider

`api/app/llm.py` talks to any OpenAI-compatible chat-completions API. Set `LLM_API_KEY`, `LLM_BASE_URL` (default: OpenRouter) and `MODEL_FAST` in `.env`. The model must support forced tool calls; if a call fails twice, that step falls back to the heuristic or template output. If only `ANTHROPIC_API_KEY` is set, Anthropic's OpenAI-compatible endpoint is used.

## Commands

| Command | What it does |
|---|---|
| `make test` | ruff + pytest (api), tsc + eslint (web). No network or API key needed. |
| `make types` | Regenerate `web/src/lib/api-types.ts` from the FastAPI schema. |
| `make sample` | Regenerate `contracts/sample_report.json` and the cached demo audits (original and fixed policy). |
| `make audit repo=. policy=FILE_OR_URL` | Run one audit from the command line; non-zero exit on a red cell. Optional `site=`, `fail_on=`, `markdown=`. |
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
