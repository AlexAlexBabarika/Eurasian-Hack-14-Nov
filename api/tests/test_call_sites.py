"""Bug: a data category was attributed to a vendor whenever its identifier appeared anywhere in a file importing
the vendor's SDK. It now has to be passed in the arguments of a call to that SDK."""

import time

from app.detect import manifests
from app.ingest.repo import RepoFile
from app.models import Observation

PKG = RepoFile(path="package.json", text='{"dependencies": {"stripe": "1", "posthog-js": "1", "openai": "1"}}')
REQS = RepoFile(path="requirements.txt", text="stripe\nopenai\nposthog\n")


def detect(path: str, *lines: str) -> dict[str, Observation]:
    manifest = REQS if path.endswith(".py") else PKG
    return {o.vendor: o for o in manifests.detect([manifest, RepoFile(path=path, text="\n".join(lines))])}


def cats(path: str, *lines: str) -> dict[str, list[str]]:
    return {vendor: o.data_categories for vendor, o in detect(path, *lines).items()}


def test_pii_elsewhere_in_a_file_that_imports_an_sdk_is_not_attributed():
    found = cats(
        "lib/billing.ts",
        'import Stripe from "stripe";',
        "const stripe = new Stripe(process.env.STRIPE_KEY);",
        "export async function cancel(user: { id: string; email: string; phone: string }) {",
        "  const row = await db.user.findUnique({ where: { email: user.email } });",
        "  await stripe.subscriptions.cancel(row.subscriptionId);",
        "}",
    )
    assert found["Stripe"] == ["payment"]
    found = cats(
        "components/login.tsx",
        'import posthog from "posthog-js";',
        "export function Login() {",
        '  posthog.capture("login_viewed");',
        "  return <input type={kind} value={email} onChange={(e) => setEmail(e.target.value)} />;",
        "}",
    )
    assert found["PostHog"] == ["usage", "device_id", "ip"]


def test_pii_inside_a_multi_line_call_is_attributed_with_call_site_evidence():
    found = detect(
        "lib/analytics.ts",
        'import posthog from "posthog-js";',
        "export function identify(user: User) {",
        "  posthog.identify(",
        "    user.id,",
        "    {",
        "      email: user.email,",
        "      name: user.name,",
        "    },",
        "  );",
        "}",
    )["PostHog"]
    assert found.data_categories == ["usage", "device_id", "ip", "email", "name"]
    passed = {e.summary: e.line for e in found.evidence if "passed to" in e.summary}
    assert passed == {"email passed to PostHog": 6, "name passed to PostHog": 7}


def test_instances_created_from_the_import_are_followed():
    js = cats(
        "lib/billing.ts",
        'const Stripe = require("stripe");',
        "const stripe = new Stripe(key);",
        "await stripe.customers.create({ email: user.email });",
    )
    assert js["Stripe"] == ["payment", "email"]
    py = cats(
        "jobs/summarise.py",
        "from openai import OpenAI",
        "client = OpenAI()",
        "def summarise(user, text):",
        "    return client.chat.completions.create(",
        '        model="gpt-4o-mini",',
        '        messages=[{"role": "user", "content": text}],',
        "        user=user.email,",
        "    )",
    )
    assert py["OpenAI"] == ["email", "user_content"]
    module = cats("jobs/bill.py", "import stripe", "stripe.Customer.create(email=user.email, phone=user.phone)")
    assert module["Stripe"] == ["payment", "email", "phone"]


def test_singletons_and_local_factories_named_after_the_sdk_are_instances():
    singleton = cats(
        "lib/posthog.ts",
        'import { PostHog } from "posthog-node";',
        "const posthog =",
        "  API_KEY",
        "    ? new PostHog(API_KEY, { host })",
        "    : null;",
        "posthog?.identify({ distinctId, properties: { email } });",
    )
    assert singleton["PostHog"] == ["usage", "device_id", "ip", "email"]
    factory = cats(
        "lib/fraud.ts",
        'import { stripeInstance } from "@/ee/stripe";',
        'import { Stripe } from "stripe";',
        "const stripeClient = stripeInstance();",
        "const rows = loadRows({ phone });",
        "await stripeClient.radar.valueListItems.create({ value: email });",
        "rows.forEach((row) => save(row.phone));",
    )
    assert factory["Stripe"] == ["payment", "email"]


def test_parameter_typed_with_the_imported_class_is_an_instance():
    found = cats(
        "lib/billing.ts",
        'import type Stripe from "stripe";',
        "export const sync = (stripe: Stripe, user: User) => stripe.customers.update(user.id, { email: user.email });",
    )
    assert found["Stripe"] == ["payment", "email"]


def test_named_and_multi_line_imports_called_directly():
    found = cats(
        "lib/track.ts",
        "import {",
        "  capture as send,",
        "  type Properties,",
        '} from "posthog-js";',
        "send('signup', { email });",
    )
    assert found["PostHog"] == ["usage", "device_id", "ip", "email"]
    hook = cats(
        "components/signup.tsx",
        'import { usePostHog } from "posthog-js/react";',
        "const posthog = usePostHog();",
        "posthog?.identify(id, { phone: form.phone });",
    )
    assert hook["PostHog"] == ["usage", "device_id", "ip", "phone"]


def test_two_vendors_in_one_file_get_only_their_own_categories():
    found = cats(
        "lib/signup.ts",
        'import Stripe from "stripe";',
        'import * as posthog from "posthog-js";',
        "const stripe = new Stripe(key);",
        "await stripe.customers.create({ email: user.email });",
        'posthog.capture("signup", { phone: user.phone });',
    )
    assert found["Stripe"] == ["payment", "email"]
    assert found["PostHog"] == ["usage", "device_id", "ip", "phone"]


def test_ai_user_content_only_at_the_ai_call():
    untouched = cats(
        "app/api/chat/route.ts",
        'import OpenAI from "openai";',
        "const openai = new OpenAI();",
        "const { messages, input } = await req.json();",
        "await db.message.create({ data: { content: input } });",
        "const models = await openai.models.list();",
    )
    assert untouched["OpenAI"] == []
    sent = detect(
        "app/api/chat/route.ts",
        'import OpenAI from "openai";',
        "const openai = new OpenAI();",
        "const { messages } = await req.json();",
        "await openai.chat.completions.create({ model, messages });",
    )["OpenAI"]
    assert sent.data_categories == ["user_content"]
    assert [e.line for e in sent.evidence if e.summary == "User-provided content passed to OpenAI"] == [4]


def test_ai_provider_handed_to_another_call_counts_as_that_call():
    found = cats(
        "app/api/chat/route.ts",
        'import { openai } from "@ai-sdk/openai";',
        'import { streamText } from "ai";',
        "const title = prompt.slice(0, 20);",
        'const result = streamText({ model: openai("gpt-4o"), prompt });',
    )
    assert found["OpenAI"] == ["user_content"]


def test_one_level_of_local_data_flow_into_a_call():
    found = detect(
        "lib/analytics.ts",
        'import posthog from "posthog-js";',
        "const props = { email: user.email, plan };",
        "const other = { phone: user.phone };",
        'posthog.capture("signup", props);',
    )["PostHog"]
    assert found.data_categories == ["usage", "device_id", "ip", "email"]
    assert [e.line for e in found.evidence if e.summary.startswith("email passed to PostHog")] == [4]


def test_callback_bodies_and_comments_inside_a_call_are_not_arguments():
    found = cats(
        "lib/flags.ts",
        'import posthog from "posthog-js";',
        "posthog.onFeatureFlags(() => {",
        "  setEmail(user.email);",
        "});",
        "posthog.capture(",
        "  // never send the email here",
        '  "viewed",',
        ");",
    )
    assert found["PostHog"] == ["usage", "device_id", "ip"]


def test_other_languages_keep_the_file_level_heuristic():
    files = [
        RepoFile(path="go.mod", text="require github.com/getsentry/sentry-go v0.27.0\n"),
        RepoFile(path="main.go", text='import "github.com/getsentry/sentry-go"\nsentry.SetUser(sentry.User{Email: u.Email})\n'),
    ]
    found = manifests.detect(files)[0]
    assert found.data_categories == ["device_id", "ip", "usage", "email"]
    assert "email handled in a file that calls Sentry" in [e.summary for e in found.evidence]


def test_unbalanced_calls_do_not_stall_the_scan():
    text = 'import posthog from "posthog-js";\n' + "posthog.capture(a, (\n" * 40_000 + "user.email"
    start = time.monotonic()
    manifests.detect([PKG, RepoFile(path="src/big.ts", text=text)])
    assert time.monotonic() - start < 2.0
