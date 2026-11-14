# Submission

Items marked TODO need a person: a link that does not exist yet, or a fact only the team knows.

## Project name and one-liner

**ProveryAI**: checks what your privacy policy says against what your code and live site actually do, under UK, EU and Kazakhstan law.

The name is the second half of the proverb *doveryai, no proveryai*: trust, but verify.

## Project description

Startups copy a privacy policy from a template, then ship Mixpanel, Sentry and OpenAI, and the policy never catches up. ProveryAI takes a GitHub repo, a live site and the policy URL, finds what the product really collects and sends, and shows each possible inconsistency with evidence (file and line, network request, policy quote), the official provision it relates to in the UK, EU and Kazakhstan, and a clause you can paste to fix it.

## Links

| Item | Link |
|---|---|
| GitHub repository | https://github.com/AlexAlexBabarika/Eurasian-Hack-14-Nov |
| Deployed prototype | TODO after deploying: https://proveryai.babarika.dev ([docs/DEPLOY.md](docs/DEPLOY.md)) |
| Demo video (under 2 min) | TODO: record with [demo/SCRIPT.md](demo/SCRIPT.md), upload unlisted, paste the link |
| Pitch deck | [docs/pitch.pdf](docs/pitch.pdf) |

## Team

Boris Sheryakov (web app, public-deployment safety, Russian and Kazakh policies), Alex Babarika (detection pipeline, rules, verdicts), Gor Vardanyan (law corpus and its verification, MCP server, GitHub Action).

## Tools used

- **API**: Python 3.12, FastAPI, Pydantic v2, Playwright (Chromium), trafilatura, rank-bm25, Bearer CLI, sse-starlette, MCP Python SDK. Tooling: uv, ruff, pytest.
- **Web**: Next.js 15, React 19, TypeScript, Tailwind v4, shadcn/ui, TanStack Query, shiki. Tooling: pnpm, ESLint, openapi-typescript.
- **Running it**: Docker, Caddy, GitHub Actions, Vercel, Hetzner.
- **LLM inside the product**: any OpenAI-compatible API through `api/app/llm.py`; we used OpenRouter (Claude Sonnet 4.5 by default, a DeepSeek flash model for the first live runs).
- **AI coding tools**: Devin wrote most of the code under our direction (its co-author line is on the commits). TODO: add any others you used (Cursor, Claude Code, ChatGPT).

## How AI was used

### In the product

The model has two narrow jobs: extract structured claims from the policy text, and write the explanation and the suggested clause for each matrix cell. Everything that decides the result is ordinary code: vendor detection, the ten diff rules, the red/amber/green status, and which provisions are cited. Quotes from the policy must be exact substrings or they are dropped; provision ids that are not in the corpus are dropped. With no API key the pipeline still runs end to end on keyword heuristics and template text.

### In building it

We wrote one brief ([PLAN.md](PLAN.md)) with frozen data contracts and a short rules file ([AGENTS.md](AGENTS.md)), then ran coding agents in parallel, one git worktree and one pull request per task (about 30 pull requests in a day).

**What worked**

- Contracts first. With `api/app/models.py` and a sample report fixed in the first half hour, the web app, the pipeline and the law corpus were built at the same time without blocking each other.
- Tests that need no network and no API key (`make test`), so every agent could check its own work.
- Giving agents real targets. Running the tool on 17 open-source products produced a concrete bug list that an agent could then fix.
- Keeping the model away from decisions. Once status and citations moved into code, the model's mistakes became wording problems instead of wrong results.

**Where it failed**

- **Law.** The AI-drafted corpus looked right and was wrong in 4 of 51 provisions when checked against the official texts: two UK GDPR articles had been replaced in February 2026, the ePrivacy link pointed at the 2002 text without the consent rule, and one summary described the wrong part of an Act. Legal references need a person to open the official page.
- **Inventing facts.** On the first live run the model wrote that data was sent "without prior consent" when no evidence showed that; it had read the policy's silence, and a raw `pre_consent=False` flag, as proof. We changed the prompt and stopped showing it the flag.
- **False positives.** The agent-written heuristics misread well-written policies. On the 17 real products most red cells were wrong at first; four reports were checked by hand and ten bugs fixed.
- **Performance.** An agent-written regex was quadratic on minified lines: one repository took 9.5 minutes in a single rule (1.7 seconds after the fix).
- **Things that had never been run.** The Docker image and the MCP server both failed on first start (a missing system library; the MCP SDK had renamed its server class).
- **Speed and cost of the model.** Hidden reasoning tokens made up 55 to 80% of each completion, so writing nine cells took 20 to 60 seconds until we turned reasoning off and capped the output (pull request #23).

TODO: read this section once as a team and correct anything that does not match what you remember; it was assembled from the commit history.
