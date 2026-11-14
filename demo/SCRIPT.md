# Demo script (3 minutes)

Setup before going on stage: `make fixture`, `make dev` (or `make demo` for the cached replay), browser on http://localhost:3000.

1. (20s) Problem. "Every startup in this room has a template privacy policy. Then the code ships Mixpanel, Sentry and OpenAI, and the policy never catches up."
2. (20s) Click "Use demo fixture", start the audit. Talk over the live timeline: clone, SDK catalog, site scan before consent, policy, law.
3. (60s) Matrix appears. Click **EU x Personal data (RED)**. "The policy says *we never share your data with third parties*. The code sends email and name to Mixpanel, `src/lib/analytics.ts:13`. PostHog fires before consent." Open the GDPR Art. 13(1)(e) link. Copy the paste-ready fix.
4. (30s) Open **UK x Personal data** and point at the cookie finding: AMBER in the UK (statistical-purposes exception added by the Data (Use and Access) Act 2025, conditions apply), RED in the EU. "Same code, different law. That is why this is not a chat wrapper."
5. (30s) **KZ x AI transparency (RED)**: user chat text goes to OpenAI with no AI disclosure; Kazakhstan AI law Art. 21. Then the data-localisation note under KZ x Personal data.
6. (20s) Export Markdown. Mention the MCP tool `audit_product`: "run it in CI before every release."

Fallback: `make demo` (`DEMO_MODE=cached`) replays `api/data/audits/demo-fixture.json` when the three demo URLs are submitted.
