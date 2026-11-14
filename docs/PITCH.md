---
marp: true
theme: default
paginate: true
class: invert
style: |
  section { font-family: Inter, -apple-system, Helvetica, Arial, sans-serif; background: #0b0d12; color: #e8e6e1; padding: 64px 72px; }
  h1 { font-size: 58px; line-height: 1.05; color: #f3efe6; }
  h2 { font-size: 40px; color: #f3efe6; }
  strong { color: #ffffff; }
  blockquote { border-left: 6px solid #d9d2c3; color: #d9d2c3; font-style: italic; font-size: 30px; }
  code { background: #171b24; color: #9fe0b4; }
  table { font-size: 24px; }
  th { background: #171b24; color: #e8e6e1; }
  td { background: #0b0d12; color: #e8e6e1; }
  .red { color: #ff6b6b; font-weight: 700; } .amber { color: #f5b942; font-weight: 700; } .green { color: #5fd38d; font-weight: 700; } .grey { color: #8a8f9c; font-weight: 700; }
  .who { position: absolute; top: 28px; right: 72px; font-size: 20px; letter-spacing: 0.08em; text-transform: uppercase; color: #8a8f9c; }
  .small { font-size: 22px; color: #8a8f9c; }
---

<!--
PITCH PLAN (3:00 total). Speaker notes for each slide are in these comments.

  Boris  0:00-0:40  slides 1-3   the problem and what ProveryAI is
  Alex   0:40-2:05  slides 4-5   live demo, then how it works
  Gor    2:05-3:00  slides 6-7   the law, where it runs, what is next

Hand-overs are one sentence each and are written into the notes.
If you get 5 minutes: Alex adds the before/after rerun (demo step 4), Gor adds the terminal CI run.
If you get 2 minutes: drop slide 5 and Alex stops the demo after the EU cell.
Wording rule: "possible inconsistency with", never "violates" or "illegal".
-->

<div class="who">Boris</div>

# ProveryAI

Your privacy policy makes promises.
**Your code keeps the receipts.**

<span class="small">Doveryai, no proveryai: trust, but verify. &nbsp;·&nbsp; Boris Sheryakov, Alex Babarika, Gor Vardanyan</span>

<!--
BORIS (10s)
"Hi, we are Boris, Alex and Gor. There is a Russian proverb: doveryai, no proveryai. Trust, but verify. We built the verify part for privacy policies."
-->

---

<div class="who">Boris</div>

## The policy is written once. The code changes every week.

> "We never share your data with third parties."

```ts
import mixpanel from "mixpanel-browser";   // src/lib/analytics.ts:1
```

Nobody compares the two until a regulator, a customer's security review or an investor's lawyer does.

<!--
BORIS (15s)
"Every startup has a privacy policy copied from a template. Then an engineer adds Mixpanel, another adds Sentry, someone wires up OpenAI. The policy still says 'we never share your data'. Nobody checks, until a regulator or an enterprise customer's security review does."
-->

---

<div class="who">Boris</div>

## Three links in, one matrix out

| | Personal data | AI transparency | Consumer | Financial |
|---|---|---|---|---|
| **UK** | <span class="red">RED</span> | <span class="amber">AMBER</span> | <span class="red">RED</span> | <span class="grey">GREY</span> |
| **EU** | <span class="red">RED</span> | <span class="red">RED</span> | <span class="red">RED</span> | <span class="grey">GREY</span> |
| **KZ** | <span class="red">RED</span> | <span class="red">RED</span> | <span class="red">RED</span> | <span class="grey">GREY</span> |

Repository + live site + privacy policy. Each cell: evidence, the official provision, a fix you can paste.

<!--
BORIS (15s)
"You give ProveryAI three links: the repository, the live site and the policy. It works out what the product actually collects and sends, compares that with what the policy claims, and gives you this: three jurisdictions, four areas of law. Website scanners only read the site. Code scanners are built for enterprises. This does both in about two minutes."
Hand-over: "Alex will run it."
-->

---

<div class="who">Alex</div>

## Live demo

1. Demo product "Notely": run the audit, watch the timeline
2. **EU x Personal data**: policy quote next to `analytics.ts:1`, GDPR Art. 13(1)(e), paste-ready fix
3. **Tracking before consent**: UK <span class="amber">AMBER</span>, EU <span class="red">RED</span>
4. Rerun with the fixed policy: what a policy edit fixes, and what needs code

<span class="small">Backup: `make demo` replays a saved audit; `/audit/demo-fixture` opens with no API.</span>

<!--
ALEX (60s) - switch to the browser, http://localhost:3000, started with `make demo` and `make fixture`.

(0:40) Click "Use demo fixture", Run. Over the timeline:
"This is Notely, a small product we wrote that makes the usual mistakes. ProveryAI reads its dependencies, loads the site without clicking anything to see what fires before consent, and extracts the claims from the policy."

(0:55) Matrix appears. Click EU x Personal data.
"EU, personal data, red. On the left the policy: 'We never share your data with third parties.' On the right the code: Mixpanel imported in analytics.ts, line 1, and five more vendors receive personal data. This is the provision it relates to, GDPR Article 13, with a link to the official text. And this is a clause you can paste into the policy."

(1:20) Close the panel, scroll to the "Tracking before consent" finding.
"Same finding, three jurisdictions. Analytics before consent is red in the EU and amber in the UK."

(1:30) Only if time: rerun with the fixed policy.
"We paste the suggested clauses and run again. AI transparency goes green. What stays needs a code change."

Back to slides.
-->

---

<div class="who">Alex</div>

## Why this is not a chat wrapper

| Step | Decided by |
|---|---|
| What the product does: SDK catalog, code signals, network requests before consent | **Code** |
| What the policy claims: quotes must be exact substrings of the policy | LLM, checked by code |
| Findings: 10 rules (undisclosed processor, tracking before consent, AI not disclosed ...) | **Code** |
| Red / amber / green and which provisions are cited | **Code** |
| The explanation and the suggested clause | LLM |

No finding without evidence. No citation from outside our corpus. Works with no LLM key at all.

<!--
ALEX (25s)
"What matters is who decides what. The facts come from the code and from real network requests. The findings come from ten deterministic rules. The colour of a cell and the provisions it cites are decided in code. The model does two things: it extracts claims from the policy, and every quote must be an exact substring or it is dropped, and it writes the explanation. Without an API key the whole thing still runs on heuristics. We ran it on 17 real open-source products and fixed the false positives we found by hand-checking."
Hand-over: "The legal side is Gor's."
-->

---

<div class="who">Gor</div>

## Same code, different law

| Evidence | UK | EU | KZ |
|---|---|---|---|
| Analytics fires before consent | <span class="amber">AMBER</span> PECR Sch. A1 para. 5: statistical-purposes exception (2025) | <span class="red">RED</span> ePrivacy Art. 5(3) | <span class="amber">AMBER</span> Personal Data Law |
| Chat text sent to OpenAI, AI not mentioned | <span class="amber">AMBER</span> no AI statute, ICO guidance | <span class="red">RED</span> AI Act Art. 50 | <span class="red">RED</span> AI Law No. 230-VIII, in force Jan 2026 |

51 provisions in the corpus, each with its official URL. 47 checked against the official text (AI-assisted; human confirmation pending); the other 4 carry a warning badge.

<!--
GOR (30s)
"The same evidence gets a different answer in each jurisdiction. Analytics before consent: red under the EU ePrivacy rules, amber in the UK, because a 2025 amendment added an exception for statistical cookies, with conditions. Chat text going to OpenAI: the UK has no AI statute, so amber at most. Kazakhstan has an AI law that came into force this January, and almost no tool covers it.
A model cannot invent a citation here. There are 51 provisions, each with a link to the official text. We checked them against those texts: the first AI-written draft had four wrong, including two UK GDPR articles that changed this February. Those four are corrected and still flagged until a second person confirms them."
-->

---

<div class="who">Gor</div>

## Where it runs, and what is next

- **Web app**: three links, a shareable report, Markdown export
- **CI**: `make audit` and a GitHub Action that fails the pull request on a red cell
- **Coding agents**: MCP tool `audit_product` for Claude Code and Cursor

**Who pays:** free scan, paid CI gate per repository, then seats for the lawyer who signs off.
**Next:** more jurisdictions, mobile apps, a GitHub App that comments when a pull request adds a new vendor.

**Not legal advice. It is the evidence you bring to your lawyer.**

<!--
GOR (25s)
"It runs in three places: the web app you saw, in CI as a GitHub Action that fails the pull request when a new undisclosed vendor appears, and as an MCP tool, so a coding agent can check before it ships. The scan is free; the CI gate is what a team would pay for.
ProveryAI is not legal advice. It is the evidence pack you bring to your lawyer. Trust your policy, but verify your code. Thank you."

Q&A - who answers what:
  Boris: product, UI, competitors, business model, PUBLIC_MODE / abuse of a public deployment.
  Alex:  detection, false positives ("every finding has file:line or a network request; too little evidence is grey, not green"), speed, LLM use.
  Gor:   law, corpus verification, why Kazakhstan, liability ("first-pass engineering check, possible inconsistencies only"), MCP and the Action.
-->
