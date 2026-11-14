"use client";

import { useId, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Check, FileText, GitBranch, Globe, LoaderCircle, TriangleAlert } from "lucide-react";
import { cn } from "cn";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, createAudit, DEMO_PORTFOLIO_ID } from "@/lib/api";
import { JURISDICTION_LABEL } from "@/lib/labels";
import type { Effort, Jurisdiction } from "@/lib/types";
import { JURISDICTIONS } from "@/lib/types";

type FieldName = "repo_url" | "site_url" | "policy_url";

type Field = { name: FieldName; label: string; hint: string; placeholder: string; icon: typeof Globe; optional?: boolean };

const FIELDS: Field[] = [
  {
    name: "repo_url",
    label: "GitHub repository",
    hint: "Public repository. We read the code, we never run it. Without it only the live site is compared with the policy, so code-level findings are not available.",
    optional: true,
    placeholder: "https://github.com/acme/app",
    icon: GitBranch,
  },
  {
    name: "site_url",
    label: "Live site",
    hint: "Opened in a clean browser: first without clicking anything, then after refusing and after accepting cookies.",
    placeholder: "https://app.acme.com",
    icon: Globe,
  },
  {
    name: "policy_url",
    label: "Privacy policy",
    hint: "The public page your users see. Without it only the checks that need no policy run: trackers and consent on the site, personal data in logs.",
    optional: true,
    placeholder: "https://acme.com/privacy",
    icon: FileText,
  },
];

type Values = Record<FieldName, string>;

const EFFORTS: { value: Effort; label: string; hint: string }[] = [
  { value: "fast", label: "Fast", hint: "The quicker model. About a minute." },
  { value: "strong", label: "Strong", hint: "The stronger model reads the policy and writes the verdicts. Slower." },
];

const DEMO_VALUES: Values = {
  repo_url: "https://github.com/AlexAlexBabarika/Eurasian-Hack-14-Nov/tree/main/demo/fixture-app",
  site_url: "http://localhost:4100/public/index.html",
  policy_url: "http://localhost:4100/privacy.html",
};

// A real product. Its repository is private, so this runs as a replay (DEMO_MODE=cached) or with GITHUB_TOKEN set.
const PORTFOLIO_VALUES: Values = {
  repo_url: "https://github.com/AlexAlexBabarika/portfolio-app",
  site_url: "https://staging.the-portfolio.app",
  policy_url: "https://staging.the-portfolio.app/privacy",
};

const PRESETS: { label: string; values: Values }[] = [
  { label: "Use The Portfolio App", values: PORTFOLIO_VALUES },
  { label: "Test fixture", values: DEMO_VALUES },
  { label: "Fixture, fixed policy", values: { ...DEMO_VALUES, policy_url: "http://localhost:4100/privacy-fixed.html" } },
];

function validate(field: Field, raw: string): string | null {
  const { name } = field;
  const value = raw.trim();
  if (!value) return field.optional ? null : "This field is required.";
  let url: URL;
  try {
    url = new URL(value);
  } catch {
    return "Enter a full address starting with https://";
  }
  if (url.protocol !== "http:" && url.protocol !== "https:") return "The address must start with http:// or https://";
  if (name === "repo_url") {
    const parts = url.pathname.split("/").filter(Boolean);
    if (url.hostname !== "github.com" || parts.length < 2) return "Use a link like https://github.com/owner/repository";
  }
  return null;
}

export function AuditForm() {
  const router = useRouter();
  const formId = useId();
  const [values, setValues] = useState<Values>({ repo_url: "", site_url: "", policy_url: "" });
  const [touched, setTouched] = useState<Partial<Record<FieldName, boolean>>>({});
  const [jurisdictions, setJurisdictions] = useState<Jurisdiction[]>(JURISDICTIONS);
  const [effort, setEffort] = useState<Effort>("fast");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<ApiError | Error | null>(null);

  const errors = Object.fromEntries(FIELDS.map((field) => [field.name, validate(field, values[field.name])])) as Record<
    FieldName,
    string | null
  >;
  const isDemo = PRESETS.some((preset) => FIELDS.every((field) => values[field.name].trim() === preset.values[field.name]));

  function toggle(jurisdiction: Jurisdiction) {
    setJurisdictions((current) =>
      current.includes(jurisdiction)
        ? current.filter((item) => item !== jurisdiction)
        : JURISDICTIONS.filter((item) => item === jurisdiction || current.includes(item)),
    );
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setTouched({ repo_url: true, site_url: true, policy_url: true });
    const firstInvalid = FIELDS.find((field) => errors[field.name]);
    if (firstInvalid) {
      document.getElementById(`${formId}-${firstInvalid.name}`)?.focus();
      return;
    }
    if (jurisdictions.length === 0) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      const { id } = await createAudit({
        repo_url: values.repo_url.trim() || null,
        site_url: values.site_url.trim(),
        policy_url: values.policy_url.trim() || null,
        jurisdictions,
        effort,
      });
      router.push(`/audit/${encodeURIComponent(id)}`);
    } catch (error) {
      setSubmitError(error instanceof Error ? error : new Error("Something went wrong."));
      setSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={submit}
      noValidate
      className="rounded-[20px] border border-white/15 bg-card p-5 shadow-2xl shadow-black/60 sm:p-6"
    >
      <div className="mb-5 flex flex-wrap items-center justify-between gap-x-3 gap-y-2">
        <h2 className="text-xl font-semibold tracking-tight text-foreground">Start an audit</h2>
        <div className="flex flex-wrap items-center gap-1.5">
          {PRESETS.map((preset) => (
            <Button
              key={preset.label}
              type="button"
              variant="outline"
              size="sm"
              className="rounded-full"
              onClick={() => {
                setValues(preset.values);
                setTouched({});
                setSubmitError(null);
              }}
            >
              {preset.label}
            </Button>
          ))}
        </div>
      </div>

      <div className="space-y-4">
        {FIELDS.map((field) => {
          const id = `${formId}-${field.name}`;
          const error = touched[field.name] ? errors[field.name] : null;
          const valid = !errors[field.name] && values[field.name].trim() !== "";
          const Icon = field.icon;
          return (
            <div key={field.name} className="space-y-1.5">
              <Label htmlFor={id}>
                {field.label}
                {field.optional && <span className="font-normal text-muted-foreground">(optional)</span>}
              </Label>
              <div className="relative">
                <Icon aria-hidden className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id={id}
                  name={field.name}
                  type="url"
                  inputMode="url"
                  autoComplete="off"
                  spellCheck={false}
                  placeholder={field.placeholder}
                  value={values[field.name]}
                  aria-invalid={Boolean(error)}
                  aria-describedby={`${id}-hint`}
                  className="h-11 bg-ink/60 pr-9 pl-9 font-mono text-[13px]"
                  onChange={(event) => setValues((current) => ({ ...current, [field.name]: event.target.value }))}
                  onBlur={() => values[field.name] && setTouched((current) => ({ ...current, [field.name]: true }))}
                />
                {valid && (
                  <Check aria-hidden className="pointer-events-none absolute top-1/2 right-3 size-4 -translate-y-1/2 text-status-green" />
                )}
              </div>
              <p id={`${id}-hint`} className={cn("text-xs", error ? "text-destructive" : "text-muted-foreground")}>
                {error ?? field.hint}
              </p>
            </div>
          );
        })}

        <fieldset className="space-y-2 pt-1">
          <legend className="text-sm font-medium text-foreground">Check against the law of</legend>
          <div className="divide-y overflow-hidden rounded-lg border">
            {JURISDICTIONS.map((jurisdiction) => {
              const checked = jurisdictions.includes(jurisdiction);
              return (
                <label
                  key={jurisdiction}
                  className={cn(
                    "flex cursor-pointer items-center gap-3 px-3 py-2.5 transition-colors has-focus-visible:bg-accent",
                    checked ? "bg-accent/40" : "hover:bg-accent/30",
                  )}
                >
                  <input type="checkbox" className="sr-only" checked={checked} onChange={() => toggle(jurisdiction)} />
                  <span
                    aria-hidden
                    className={cn(
                      "flex size-4 shrink-0 items-center justify-center rounded border",
                      checked ? "border-primary bg-primary text-primary-foreground" : "border-input",
                    )}
                  >
                    {checked && <Check className="size-3" strokeWidth={3} />}
                  </span>
                  <span className={cn("text-sm font-medium", checked ? "text-foreground" : "text-muted-foreground")}>
                    {JURISDICTION_LABEL[jurisdiction].name}
                  </span>
                  <span className="ml-auto truncate text-xs text-muted-foreground">{JURISDICTION_LABEL[jurisdiction].laws}</span>
                </label>
              );
            })}
          </div>
          {jurisdictions.length === 0 && <p className="text-xs text-destructive">Select at least one jurisdiction.</p>}
        </fieldset>

        <fieldset className="space-y-2 pt-1">
          <legend className="text-sm font-medium text-foreground">Effort</legend>
          <div className="grid grid-cols-2 gap-2">
            {EFFORTS.map((option) => {
              const checked = effort === option.value;
              return (
                <label
                  key={option.value}
                  className={cn(
                    "cursor-pointer rounded-lg border px-3 py-2.5 transition-colors has-focus-visible:ring-3 has-focus-visible:ring-ring/50",
                    checked ? "border-primary bg-accent/40" : "hover:bg-accent/30",
                  )}
                >
                  <input
                    type="radio"
                    name={`${formId}-effort`}
                    className="sr-only"
                    checked={checked}
                    onChange={() => setEffort(option.value)}
                  />
                  <span className={cn("block text-sm font-medium", checked ? "text-foreground" : "text-muted-foreground")}>
                    {option.label}
                  </span>
                  <span className="block text-xs text-muted-foreground">{option.hint}</span>
                </label>
              );
            })}
          </div>
        </fieldset>
      </div>

      {submitError && (
        <div role="alert" className="mt-5 flex gap-2.5 rounded-lg border border-status-amber/35 bg-status-amber/10 p-3 text-sm">
          <TriangleAlert aria-hidden className="mt-0.5 size-4 shrink-0 text-status-amber" />
          <div className="space-y-2">
            <p className="text-foreground">{submitError.message}</p>
            {submitError instanceof ApiError && submitError.kind === "network" && (
              <p className="text-muted-foreground">
                Start the API with <code className="rounded bg-muted px-1 py-0.5 font-mono text-xs">make api</code>. If it is
                already running, add this page&apos;s address to{" "}
                <code className="rounded bg-muted px-1 py-0.5 font-mono text-xs">WEB_ORIGINS</code> in{" "}
                <code className="rounded bg-muted px-1 py-0.5 font-mono text-xs">.env</code> and restart it. Or look at a
                recorded audit of The Portfolio App.
              </p>
            )}
            <Button type="button" variant="outline" size="sm" onClick={() => router.push(`/audit/${DEMO_PORTFOLIO_ID}`)}>
              Open the recorded demo audit
            </Button>
          </div>
        </div>
      )}

      <div className="mt-6 space-y-2.5">
        <Button
          type="submit"
          size="lg"
          className="group/run arc-border tone-signal h-12 w-full rounded-xl text-base font-semibold hover:bg-primary hover:brightness-110"
          disabled={submitting || jurisdictions.length === 0}
        >
          {submitting ? <LoaderCircle aria-hidden className="animate-spin" /> : null}
          {submitting ? "Starting…" : isDemo ? "Run demo audit" : "Run audit"}
          {!submitting && <ArrowRight aria-hidden className="transition-transform group-hover/run:translate-x-1" />}
        </Button>
        <p className="text-center text-xs text-muted-foreground">
          {effort === "strong" ? "Takes longer than a fast run." : "Takes about a minute."}
        </p>
      </div>
    </form>
  );
}
