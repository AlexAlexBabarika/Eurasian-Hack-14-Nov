"""Regressions from running the tool on real open-source products (Rallly, Hoppscotch, Papermark, monorepos)."""

import asyncio
import time

import httpx

from app.claims.extract import heuristic
from app.detect import code_signals, manifests, trackers
from app.detect.code_signals import CodeSignals
from app.diff.rules import run_rules
from app.ingest import policy, repo
from app.ingest.repo import RepoFile
from app.ingest.site import SiteScan
from app.models import AREAS, Evidence, Observation
from app.verdict.engine import deterministic_cell

RALLLY_STYLE = (
    "We do not share your personal data with any third parties for marketing or commercial purposes. "
    "We use the following sub-processors to run the service: Vercel (United States), Amazon Web Services "
    "(United States), Stripe (United States). Your data is stored on servers located in the United States."
)


def obs(vendor: str, country: str = "US") -> Observation:
    ev = [Evidence(kind="manifest", summary="dep", file="package.json", line=1)]
    return Observation(id=f"o-{vendor}", vendor=vendor, vendor_country=country, data_categories=["email"],
                       purpose_guess="infrastructure", evidence=ev)  # fmt: skip


def rules_fired(policy_text: str, vendors: list[str]) -> list[str]:
    findings = run_rules([obs(v) for v in vendors], heuristic(policy_text), CodeSignals(), "https://x.test/privacy")
    return [f.rule.split("_")[0] for f in findings]


# Bug 1: a qualified "we do not share ... for marketing" sentence is not a blanket no-sharing claim.
def test_qualified_no_sharing_sentence_is_not_no_sharing():
    assert heuristic(RALLLY_STYLE).sharing_statement == "processors_only"
    assert heuristic("We do not sell or share your data for advertising purposes.").sharing_statement == "unclear"
    assert "R2" not in rules_fired(RALLLY_STYLE, ["Stripe"])
    twenty = ("However, as noted above, Twenty does not sell your personal information to third parties, and we do "
              "not share it for cross-context behavioral advertising.")  # fmt: skip
    assert heuristic(twenty).sharing_statement != "no_sharing"
    umami = "We will not sell or share personal information in the future belonging to website visitors and users."
    assert heuristic(umami).sharing_statement != "no_sharing"


def test_blanket_no_sharing_sentence_still_counts():
    assert heuristic("We never share your data with third parties.").sharing_statement == "no_sharing"
    assert heuristic("We do not share your personal information with anyone.").sharing_statement == "no_sharing"


# Bug 2: a policy naming the company ("Vercel", "Amazon Web Services") covers that company's SDK.
def test_company_names_in_policy_match_catalog_vendors():
    text = RALLLY_STYLE.replace("sub-processors", "companies")  # no category of recipients: R1 must rely on names
    claims = heuristic(text)
    assert {"Vercel", "Amazon Web Services", "Stripe"} <= set(claims.named_processors)
    assert "R1" not in rules_fired(text, ["Vercel Analytics", "AWS SDK", "Stripe"])
    assert "R1" in rules_fired(text, ["Vercel Analytics", "Mixpanel"])


def test_alias_matching_respects_word_boundaries():
    assert "R1" in rules_fired("We store reports in Metabase and nothing else is shared here.", ["Meta Pixel"])


# Bug 3: transfer disclosures phrased as server location or as a section heading.
def test_transfer_disclosure_variants_are_recognised():
    assert heuristic(RALLLY_STYLE).international_transfers
    assert heuristic("International data transfer\nYour information may be processed elsewhere.").international_transfers
    assert heuristic("Our providers: Stripe (United States), Resend (United States).").international_transfers
    assert not heuristic("We collect your email address to create your account.").international_transfers
    assert "R6" not in rules_fired(RALLLY_STYLE, ["Stripe"])


# Bug 4: the logs rule needs a personal-data identifier in code, not the word inside a message string.
def test_logs_rule_ignores_words_inside_message_strings():
    src = "\n".join([
        'logger.error("Queued email delivery failed");',
        "console.log('sending password reset email');",
        'console.log("login attempt", user.email);',
        "console.info(`signed in ${session.user.email}`);",
        'log.info(f"created account for {user.email}")',
        'log.info(f"email queue drained in {elapsed}s")',
    ])  # fmt: skip
    hits = code_signals.detect([RepoFile(path="src/auth.ts", text=src)]).pii_logs
    assert [e.line for e in hits] == [3, 4, 5]


# Bug 5: data categories come from identifiers, not from words inside prompts and other string literals.
def test_categories_ignore_words_inside_string_literals():
    files = [
        RepoFile(path="package.json", text='{"dependencies": {"openai": "^4"}}'),
        RepoFile(path="src/moderation.ts", text="\n".join([
            'import OpenAI from "openai";',
            'const system = "Flag content that asks for a phone number or an email address";',
            "await client.chat.completions.create({ model, messages: [{ role: 'user', content: text }] });",
        ])),
    ]  # fmt: skip
    cats = manifests.detect(files)[0].data_categories
    assert "phone" not in cats and "email" not in cats
    assert "user_content" in cats


def test_multi_line_prompts_and_docstrings_are_not_code():
    ts = [
        "const SYSTEM = `You are a moderator.",
        "Flag anything asking for a phone number or email.",
        "The owner is ${owner.email}.",
        "Done.`; const phone = input.phone;",
        "const x = `one ${a} line`;",
    ]
    assert manifests.code_lines(ts) == ["const SYSTEM = ", "", "owner.email", " ; const phone = input.phone;", "const x = a;"]
    py = ['def f(user):', '    """Send the email.', '    Uses the phone number."""', '    return user.email', "x = \'\'\'a\'\'\' + user.phone"]
    assert manifests.code_lines(py) == ["def f(user):", "    ", " ", "    return user.email", 'x = "" + user.phone']


# Bug 6: when a repo is over the file cap, manifests and source files win over everything else.
def test_file_cap_keeps_manifests_and_source_before_other_files(tmp_path, monkeypatch):
    monkeypatch.setattr(repo, "MAX_FILES", 4)
    for name in ["a.md", "b.md", "c.md", "docs/d.md", "assets/logo.png"]:
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text("filler")
    (tmp_path / "zz/apps/web/src").mkdir(parents=True)
    (tmp_path / "zz/apps/web/package.json").write_text('{"dependencies": {"posthog-js": "1"}}')
    (tmp_path / "zz/apps/web/src/analytics.ts").write_text('import posthog from "posthog-js";')
    (tmp_path / "zz/apps/web/src/analytics.test.ts").write_text('import posthog from "posthog-js";')
    files, total = repo.walk(tmp_path)
    paths = [f.path for f in files]
    assert total == 7 and len(files) == 4  # the .png is never a candidate
    assert paths[:3] == ["zz/apps/web/package.json", "zz/apps/web/src/analytics.ts", "zz/apps/web/src/analytics.test.ts"]
    assert [o.vendor for o in manifests.detect(files)] == ["PostHog"]


# Bug 7: a policy that links to a separate subprocessor page is judged with that page included.
def test_linked_subprocessor_page_is_read(monkeypatch):
    pages = {
        "https://acme.test/privacy": "<html><body><main><h1>Privacy Policy</h1><p>We collect your email address "
        "to create your account and to send you service messages about your account and billing.</p><p>See our "
        '<a href="/subprocessors">list of subprocessors</a> or <a href="https://evil.test/subprocessors">this</a>. '
        '<a href="/terms">Terms</a></p></main></body></html>',
        "https://acme.test/subprocessors": "<html><body><main><h1>Subprocessors</h1><p>We use PostHog for product "
        "analytics and OpenAI for AI features. Both companies process personal data only on our behalf.</p>"
        "</main></body></html>",
    }
    requested = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        return httpx.Response(200, text=pages[str(request.url)]) if str(request.url) in pages else httpx.Response(404)

    monkeypatch.setattr(policy, "_transport", httpx.MockTransport(handler))
    text = asyncio.run(policy.fetch("https://acme.test/privacy"))
    assert requested == ["https://acme.test/privacy", "https://acme.test/subprocessors"]  # same site only
    assert "OpenAI for AI features" in text and "https://acme.test/subprocessors" in text
    assert {"PostHog", "OpenAI"} <= set(heuristic(text).named_processors)


# Found while re-running the real targets: a whole-repo URL failed to clone on macOS, where the temp dir is a symlink.
def test_scan_root_through_a_symlinked_clone_dir(tmp_path):
    real = tmp_path / "real"
    (real / "apps" / "web").mkdir(parents=True)
    link = tmp_path / "link"
    link.symlink_to(real)
    assert repo.scan_root(link, None) == real.resolve()
    assert repo.scan_root(link, "apps/web") == (real / "apps" / "web").resolve()
    for bad in ["missing", "../real/../.."]:
        try:
            repo.scan_root(link, bad)
        except ValueError:
            continue
        raise AssertionError(f"{bad} should be rejected")


def test_no_deletion_finding_needs_scanned_code():
    claims = heuristic("We collect your email address to create your account.")
    rules = lambda n: [f.rule.split("_")[0] for f in run_rules([], claims, CodeSignals(), "https://x.test/p", n)]  # noqa: E731
    assert "R7" in rules(120) and "R7" not in rules(0)


# Found on Twenty: the clone timed out, nothing was scanned, and the matrix came back green.
def test_unreadable_inputs_are_never_green():
    for area in AREAS:
        cell = deterministic_cell("EU", area, [], [], gaps=["the repository could not be read"])
        assert cell.status == "grey", area
    assert "repository could not be read" in deterministic_cell("EU", "consumer", [], [], gaps=["the repository could not be read"]).headline
    assert deterministic_cell("EU", "consumer", [], []).status == "green"


# Found on Hoppscotch and Papermark: gtag.js is served from googletagmanager.com for Analytics (G-) and Ads (AW-).
def test_google_tags_are_told_apart_by_id():
    scan = SiteScan(url="https://acme.test", requests=[
        "https://www.googletagmanager.com/gtag/js?id=G-LQ01D3PKKN&l=dataLayer",
        "https://www.googletagmanager.com/gtag/js?id=AW-17198795665&cx=c",
        "https://www.googletagmanager.com/gtm.js?id=GTM-WH2DMPB6",
    ])  # fmt: skip
    found = {o.vendor: o.purpose_guess for o in trackers.detect(scan)}
    assert found == {"Google Analytics": "analytics", "Google Ads": "ads", "Google Tag Manager": "analytics"}


# Found on Papermark: `import Stripe from "@/components/shared/icons/stripe"` was reported as the Stripe SDK.
def test_js_default_import_of_a_local_file_is_not_an_sdk_import():
    files = [
        RepoFile(path="package.json", text='{"dependencies": {"stripe": "^17"}}'),
        RepoFile(path="components/upgrade.tsx", text='import Stripe from "@/components/shared/icons/stripe";\n'),
        RepoFile(path="lib/billing.ts", text='import Stripe from "stripe";\n'),
        RepoFile(path="jobs/sync.py", text="import stripe\n"),
    ]
    code = [e.file for e in manifests.detect(files)[0].evidence if e.kind == "code"]
    assert code == ["lib/billing.ts", "jobs/sync.py"]


# Found on the 14-product re-run: most log hits were seed scripts, migrations and CLIs, or `email.subject`.
def test_logs_rule_skips_dev_tooling_and_message_objects():
    line = "console.log(`created ${user.email}`);"
    files = [RepoFile(path=p, text=line) for p in [
        "scripts/seed-utils.ts", "packages/prisma/seed-pbac-only.ts", "packages/database/src/seed.ts",
        "apps/api/migrations/normalize/normalize.migration.ts", "docker/box/src/cli/user.ts", "src/auth.test.ts",
        "apps/web/lib/sync-user-plan.ts",
    ]]  # fmt: skip
    files.append(RepoFile(path="packages/emails/src/send.ts", text="\n".join([
        'console.error(`Error sending email "${email.subject}":`, error);',
        "logger.warn(message, body.email.toLowerCase(), body.name);",
    ])))  # fmt: skip
    hits = [(e.file, e.line) for e in code_signals.detect(files).pii_logs]
    assert hits == [("apps/web/lib/sync-user-plan.ts", 1), ("packages/emails/src/send.ts", 2)]


# Found on Twenty: one audit took 9.5 minutes, all of it in the string-literal regex on minified lines.
def test_minified_lines_do_not_stall_the_scan():
    minified = "var a='x" + "\\'y\"z`" * 60_000 + ";console.log(user.email)"
    files = [RepoFile(path="src/vendor.min.js", text=minified + "\nconsole.log(user.email);")]
    start = time.monotonic()
    hits = code_signals.detect(files).pii_logs
    manifests.code_lines(minified.splitlines())
    assert time.monotonic() - start < 1.0
    assert [e.line for e in hits] == [2]
