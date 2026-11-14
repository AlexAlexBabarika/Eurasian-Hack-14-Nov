# Groundtruth: guide for judges

Groundtruth checks whether a product's privacy policy matches what its code and live site do, and maps each
mismatch to UK, EU and Kazakhstan law. This guide shows every feature in about five minutes.

Not legal advice: results are worded as possible inconsistencies for a lawyer to review.

## Fastest path

The web app has the same tour built in. Open the site, click "Judging this? Take the guided tour" at the bottom of
the landing page (or go to `/tour`), and press "Start the guided tour". A small panel in the corner then tells you
what to click at each step.

The tour uses a recorded audit that is bundled with the web app, so steps 1 to 8 work without the audit service.

To run it yourself (needs `uv`, `pnpm`, Node 20+):

```sh
make setup
make dev        # web on http://localhost:3000, audit service on :8000
make fixture    # second terminal: serves the demo product on :4100, needed only for step 9
```

## The nine steps

The demo product is Notely, a small app we wrote with planted problems (`demo/fixture-app`).

| # | Where | Do this | What it shows |
|---|---|---|---|
| 1 | `/` | Look at the "Start an audit" form | Inputs are a GitHub repository, a live site and a privacy policy. The repository or the site can be left out. |
| 2 | `/audit/demo-fixture` | Watch the steps, or press "Skip to the report" | The stages of an audit: read the code, load the site without clicking anything, read the policy, compare, map to law. |
| 3 | same page | Read the large number and the grid | One verdict per country and area of law. Financial licensing is "Not assessed" in every row, because it cannot be judged from code. |
| 4 | same page | Click the European Union / Personal data cell; open "Evidence", "Law", "How to fix" | The policy sentence next to the file and line that contradicts it, the provision with a link to the official text, and a policy clause to copy. |
| 5 | same page | In the "Findings" tab, find "Tracking before consent" | The same trackers are rated "Needs review" in the UK and "Possible inconsistency" in the EU. UK law has an exception for statistics-only analytics; EU law has none. |
| 6 | same page | Click the Kazakhstan / AI transparency cell; open "Law" | Chat text goes to an AI provider and the policy never mentions AI. Kazakhstan's AI law is cited; the UK cell is only "Needs review" because the UK has no AI statute. |
| 7 | same page | Open "Policy vs. product", then "Data flows" | What the policy claims against what was observed, and each kind of data traced to the company and country that receive it. |
| 8 | `/audit/demo-fixture-fixed?before=demo-fixture` | Read "Before and after" and the "Was:" lines in the grid | The same product with a corrected policy: 9 findings become 2. The two that remain need a code change, which a policy edit cannot fix. |
| 9 | `/` | Click "Use demo fixture", then "Run demo audit" | A live audit. Needs `make dev` and `make fixture`. A finished live report has "Download report" in the header. |

## Outside the web page

- **Release gate.** The same audit from a terminal; it exits with an error when a result is bad enough.
  ```sh
  make audit repo=demo/fixture-app policy=demo/fixture-app/privacy.html        # fails
  make audit repo=demo/fixture-app policy=demo/fixture-app/privacy-fixed.html  # passes
  ```
- **GitHub Action.** `action.yml` runs the same audit on pull requests.
- **AI assistants.** `mcp/server.py` exposes the audit as one tool, `audit_product`. Setup is in `mcp/README.md`.

## Real products

The landing page lists recorded audits of real open-source products (Hoppscotch, Papermark) when the audit service
is running. Those were produced by the same pipeline; only the Hoppscotch and Papermark findings were checked by hand.

## Keeping this file current

The in-app tour reads its numbers from the bundled audits (`web/src/lib/tour.ts`). This file is written by hand:
if the demo audits are regenerated and the counts change, update steps 5, 6 and 8 here.
