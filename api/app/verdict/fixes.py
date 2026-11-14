"""Template fixes per rule. Used when no LLM is configured, and as the fallback when LLM output is rejected."""

from app.models import Finding, Fix, Jurisdiction, Observation

REGION = {"UK": "the UK", "EU": "the European Economic Area", "KZ": "Kazakhstan"}
PURPOSE = {"analytics": "product analytics", "error_monitoring": "error monitoring", "ai_processing": "AI features",
           "payments": "payments", "ads": "advertising", "session_replay": "session recording",
           "support": "customer support", "auth": "sign-in", "infrastructure": "hosting", "maps": "embedded maps",
           "personalisation": "personalised recommendations"}  # fmt: skip


def _describe(o: Observation) -> str:
    cats = ", ".join(c.replace("_", " ") for c in o.data_categories) or "technical data"
    return f"{o.vendor} ({PURPOSE.get(o.purpose_guess or '', o.purpose_guess or 'service provider')}; receives {cats})"


def _where(f: Finding) -> str:
    e = next((e for e in f.evidence if e.file), None)
    return f"{e.file}:{e.line}" if e and e.line else (e.file if e else "the relevant code")


def template_fixes(f: Finding, j: Jurisdiction, observations: list[Observation]) -> list[Fix]:
    obs = [o for o in observations if o.id in f.observation_ids]
    vendors = "; ".join(_describe(o) for o in obs)
    names = ", ".join(o.vendor or "" for o in obs)
    match f.rule.split("_")[0]:
        case "R1":
            return [Fix(policy_clause=f"We use the following service providers to run our service: {vendors}. They "
                        "process personal data on our behalf and only on our instructions.", code_change=None)]  # fmt: skip
        case "R2":
            return [Fix(
                policy_clause="We share personal data with service providers who process it on our behalf: "
                f"{vendors}. We do not sell your personal data.",
                code_change=f"Or stop the sharing: send a pseudonymous user id instead of email/name (see {_where(f)}).",
            )]  # fmt: skip
        case "R3":
            cats = f.title.split(": ")[-1].replace("_", " ")
            return [Fix(policy_clause=f"We collect and process the following categories of personal data: {cats}. "
                        "We use them to [purposes].", code_change=None)]  # fmt: skip
        case "R4":
            ai = ", ".join(f"{o.vendor} (based in {o.vendor_country})" for o in obs)
            return [Fix(
                policy_clause="Some features of our service use artificial intelligence. When you use them, the "
                f"content you submit is sent to {ai}, which processes it to generate a response.",
                code_change=f"Show a visible notice in the product that responses are AI-generated (feature at {_where(f)}).",
            )]  # fmt: skip
        case "R5":
            opt = ("You can object to these cookies at any time in [cookie settings]." if j == "UK"
                   else "We only set them after you give consent, and you can withdraw consent at any time in "
                        "[cookie settings].")  # fmt: skip
            return [Fix(
                policy_clause=f"We use {names} to measure how our website is used. {opt}",
                code_change=f"Load {names} only after the visitor makes a choice in the consent banner; do not "
                "set their cookies or send requests on first page load.",
            )]  # fmt: skip
        case "R6":
            abroad = ", ".join(f"{o.vendor} ({o.vendor_country})" for o in obs)
            return [Fix(
                policy_clause=f"Some of our service providers are based outside {REGION[j]}: {abroad}. When we "
                "transfer personal data to them we rely on [transfer mechanism].",
                code_change="Confirm that personal data of users in Kazakhstan is stored in a database located in "
                "Kazakhstan." if j == "KZ" else None,
            )]  # fmt: skip
        case "R7":
            return [Fix(
                policy_clause="You can delete your account and personal data at any time from [Settings > Account] "
                "or by emailing [contact address]. We delete your data within [period].",
                code_change="Add a delete-account endpoint (for example DELETE /api/account) that removes the "
                "user's data, including at third-party vendors.",
            )]  # fmt: skip
        case "R8":
            return [Fix(policy_clause=None, code_change=f"Remove personal data from the log statement at {_where(f)}; "
                        "log an internal user id instead.")]  # fmt: skip
        case "R9":
            return [Fix(policy_clause="We keep your account data for as long as your account is active and delete "
                        "it within [period] after you close it. Analytics data is kept for [period].",
                        code_change=None)]  # fmt: skip
        case "R10":
            return [Fix(policy_clause=None, code_change=f"Read the visitor's stored consent choice before loading "
                        f"{names}. After a refusal, do not load the tag, send its requests or set its cookies, "
                        "on this page and on every later page load.")]  # fmt: skip
    return []
