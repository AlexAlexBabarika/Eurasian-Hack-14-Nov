# Demo script (3 minutes)

Setup before going on stage: `make fixture`, `make dev` (or `make demo` for the cached replay), browser on http://localhost:3000, a terminal at the repo root for step 7.

1. (15s) Problem. "Every startup in this room has a template privacy policy. Then the code ships Mixpanel, Sentry and OpenAI, and the policy never catches up."
2. (20s) Click "Use demo fixture", start the audit. Talk over the live timeline: clone, SDK catalog, site scan before consent, policy, law.
3. (45s) Matrix appears. Click **EU x Personal data (RED)**. "The policy says *we never share your data with third parties*. The code imports the Mixpanel SDK, `src/lib/analytics.ts:1`, and five other vendors receive personal data. PostHog fires before consent." Open the GDPR Art. 13(1)(e) link. Copy the paste-ready fix.
4. (25s) Close the panel and scroll to the Findings list. On the "Tracking before consent" card the chips read UK AMBER, EU RED, KZ AMBER. For the reason, open **UK x Personal data**, Law tab: PECR Sch. A1 para. 5, the statistical-purposes exception added by the Data (Use and Access) Act 2025 (conditions apply). "Same code, different law. That is why this is not a chat wrapper."
5. (20s) **KZ x AI transparency (RED)**: user chat text goes to OpenAI with no AI disclosure; Kazakhstan AI law Art. 21. Then the data-localisation note under KZ x Personal data.
6. (30s) Before/after. Rerun with the policy URL changed to `http://localhost:4100/privacy-fixed.html` (the same policy with the suggested clauses pasted in). The matrix goes from mostly red to UK AMBER / EU RED on personal data and GREEN on AI transparency. "The policy is fixed. The two remaining findings, trackers before consent and an email in the logs, need code changes."
7. (25s) CI. In a terminal: `make audit repo=demo/fixture-app policy=demo/fixture-app/privacy.html` fails with the red matrix; the same command with `privacy-fixed.html` passes. "The same check is a GitHub Action and an MCP tool, `audit_product`, so it runs on every pull request or from your coding agent." Export Markdown if there is time.

Fallback: `make demo` (`DEMO_MODE=cached`) replays `api/data/audits/demo-fixture.json` when the three demo URLs are submitted, and `demo-fixture-fixed.json` when the policy URL is the fixed one. Step 7 is offline either way.
