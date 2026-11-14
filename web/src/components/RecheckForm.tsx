"use client";

import { useId, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, LoaderCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, createAudit, DEMO_FIXED_ID, DEMO_ID } from "@/lib/api";
import { matrixJurisdictions } from "@/lib/status";
import type { AuditReport } from "@/lib/types";

function text(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}

function suggestedPolicyUrl(current: string | null): string {
  if (!current) return "";
  try {
    const url = new URL(current);
    if (url.host === "localhost:4100" && url.pathname.endsWith("/privacy.html")) {
      url.pathname = url.pathname.replace(/\/privacy\.html$/, "/privacy-fixed.html");
      return url.toString();
    }
  } catch {}
  return current;
}

export function RecheckForm({ id, report }: { id: string; report: AuditReport }) {
  const router = useRouter();
  const inputId = useId();
  const [policyUrl, setPolicyUrl] = useState(() => suggestedPolicyUrl(text(report.inputs.policy_url)));
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  if (id === DEMO_ID) {
    return (
      <Link
        href={`/audit/${DEMO_FIXED_ID}?before=${DEMO_ID}`}
        className="inline-flex items-center gap-1.5 rounded-md border px-3 py-2 text-sm text-foreground transition-colors outline-none hover:bg-accent/50 focus-visible:ring-3 focus-visible:ring-ring/50"
      >
        See this product after the policy fix
        <ArrowRight aria-hidden className="size-4" />
      </Link>
    );
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    const value = policyUrl.trim();
    if (!/^https?:\/\/\S+$/.test(value)) {
      setError(new Error("Enter the full address of the policy, starting with http:// or https://."));
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const created = await createAudit({
        repo_url: text(report.inputs.repo_url),
        site_url: text(report.inputs.site_url),
        policy_url: value,
        jurisdictions: matrixJurisdictions(report.matrix),
      });
      router.push(`/audit/${encodeURIComponent(created.id)}?before=${encodeURIComponent(id)}`);
    } catch (caught) {
      setError(caught instanceof Error ? caught : new Error("Something went wrong."));
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={submit} noValidate className="w-full space-y-1.5 lg:max-w-md">
      <Label htmlFor={inputId} className="text-xs text-muted-foreground">
        Re-check with an updated policy
      </Label>
      <div className="flex gap-2">
        <Input
          id={inputId}
          type="url"
          inputMode="url"
          autoComplete="off"
          spellCheck={false}
          placeholder="https://acme.com/privacy"
          value={policyUrl}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? `${inputId}-error` : undefined}
          className="font-mono text-xs md:text-xs"
          onChange={(event) => setPolicyUrl(event.target.value)}
        />
        <Button type="submit" variant="outline" disabled={submitting}>
          {submitting && <LoaderCircle aria-hidden className="animate-spin" />}
          {submitting ? "Starting" : "Re-check"}
        </Button>
      </div>
      {error && (
        <p id={`${inputId}-error`} role="alert" className="text-xs text-destructive">
          {error.message}
          {error instanceof ApiError && error.kind === "network" && (
            <>
              {" "}
              Start the API with <code className="rounded bg-muted px-1 py-0.5 font-mono">make api</code>, or, if it is
              running, add this page&apos;s address to <code className="rounded bg-muted px-1 py-0.5 font-mono">WEB_ORIGINS</code>{" "}
              and restart it.
            </>
          )}
        </p>
      )}
    </form>
  );
}
