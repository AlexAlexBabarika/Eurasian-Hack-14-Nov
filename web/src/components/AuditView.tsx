"use client";

import { useState } from "react";
import Link from "next/link";
import { Download, ExternalLink, FileText, GitBranch, Globe, Plus, TriangleAlert } from "lucide-react";
import { cn } from "cn";

import { CellSheet } from "@/components/CellSheet";
import { FindingCard } from "@/components/FindingCard";
import type { CellKey } from "@/components/Matrix";
import { Matrix } from "@/components/Matrix";
import { ProgressTimeline } from "@/components/ProgressTimeline";
import { ObservationsPanel, PolicyClaimsPanel } from "@/components/SaysVsDoes";
import { SiteHeader } from "@/components/SiteHeader";
import { Button, buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { DEMO_ID, markdownUrl } from "@/lib/api";
import { SEVERITY_LABEL, SEVERITY_ORDER } from "@/lib/labels";
import { STATUS_STYLE } from "@/lib/status";
import type { AuditReport, Severity, Status } from "@/lib/types";
import { useAudit } from "@/lib/useAudit";

function shortUrl(url: string): string {
  try {
    const parsed = new URL(url);
    const path = parsed.pathname.replace(/\/$/, "");
    return parsed.hostname === "github.com" ? path.slice(1) : `${parsed.host}${path}`;
  } catch {
    return url;
  }
}

function InputLink({ icon: Icon, label, url }: { icon: typeof Globe; label: string; url: unknown }) {
  // `inputs` is an untyped dict in the API schema.
  if (typeof url !== "string" || !/^https?:\/\//.test(url)) return null;
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="group inline-flex max-w-full items-center gap-1.5 rounded-md text-sm text-muted-foreground outline-none hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50"
    >
      <Icon aria-hidden className="size-3.5 shrink-0" />
      <span className="sr-only">{label}:</span>
      <span className="truncate font-mono text-xs">{shortUrl(url)}</span>
      <ExternalLink aria-hidden className="size-3 shrink-0 opacity-0 group-hover:opacity-100" />
    </a>
  );
}

function Stat({ value, label, tone }: { value: string; label: string; tone?: Status }) {
  return (
    <div className="rounded-lg border bg-card px-3.5 py-3">
      <p className={cn("text-2xl font-semibold tracking-tight tabular-nums", tone ? STATUS_STYLE[tone].text : "text-foreground")}>
        {value}
      </p>
      <p className="text-xs text-muted-foreground">{label}</p>
    </div>
  );
}

function Shell({ children, actions }: { children: React.ReactNode; actions?: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col">
      <SiteHeader>
        {actions}
        <Link href="/" className={buttonVariants({ variant: "outline", size: "sm" })}>
          <Plus aria-hidden />
          New audit
        </Link>
      </SiteHeader>
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6">{children}</main>
    </div>
  );
}

function Running({ id, events, skip }: { id: string; events: Parameters<typeof ProgressTimeline>[0]["events"]; skip?: () => void }) {
  return (
    <Shell>
      <div className="grid gap-8 lg:grid-cols-[minmax(0,400px)_minmax(0,1fr)] lg:gap-12">
        <section className="space-y-6">
          <div className="space-y-1.5">
            <h1 className="text-xl font-semibold tracking-tight text-foreground">Audit in progress</h1>
            <p className="text-sm text-muted-foreground">
              {id === DEMO_ID
                ? "Replaying a recorded audit of the demo project."
                : "This usually takes about a minute. You can keep this tab open in the background."}
            </p>
          </div>
          <ProgressTimeline events={events} />
          {skip && (
            <Button variant="outline" size="sm" onClick={skip}>
              Skip to the report
            </Button>
          )}
        </section>
        <section aria-hidden className="hidden space-y-3 opacity-60 lg:block">
          <Skeleton className="h-5 w-64" />
          <div className="grid grid-cols-4 gap-3">
            {Array.from({ length: 12 }, (_, i) => (
              <Skeleton key={i} className="h-[124px] rounded-lg" />
            ))}
          </div>
          <p className="pt-2 text-xs text-muted-foreground">The results matrix appears here when the audit finishes.</p>
        </section>
      </div>
    </Shell>
  );
}

function Failed({ message, retry }: { message: string; retry: () => void }) {
  return (
    <Shell>
      <div role="alert" className="mx-auto max-w-lg space-y-4 rounded-xl border bg-card p-6 text-center">
        <TriangleAlert aria-hidden className="mx-auto size-6 text-status-amber" />
        <div className="space-y-1.5">
          <h1 className="text-lg font-medium text-foreground">This audit could not be loaded</h1>
          <p className="text-sm text-muted-foreground">{message}</p>
        </div>
        <div className="flex flex-wrap justify-center gap-2">
          <Button onClick={retry}>Try again</Button>
          <Link href={`/audit/${DEMO_ID}`} className={buttonVariants({ variant: "outline" })}>
            Open the recorded demo audit
          </Link>
        </div>
      </div>
    </Shell>
  );
}

const SEVERITIES: Severity[] = ["high", "medium", "low"];

function Report({ id, report }: { id: string; report: AuditReport }) {
  const [selected, setSelected] = useState<CellKey | null>(null);
  const [severity, setSeverity] = useState<Severity | "all">("all");

  const count = (status: Status) => report.matrix.filter((cell) => cell.status === status).length;
  const red = count("red");
  const amber = count("amber");
  const assessed = report.matrix.length - count("grey");
  const findings = [...report.findings].sort((a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity]);
  const visible = severity === "all" ? findings : findings.filter((finding) => finding.severity === severity);
  const { stats, inputs } = report;

  const headline =
    red > 0
      ? `${red} of ${assessed} assessed areas show a possible inconsistency`
      : amber > 0
        ? `${amber} of ${assessed} assessed areas need review`
        : assessed > 0
          ? "No issues found in the assessed areas"
          : "Nothing could be assessed";

  return (
    <Shell
      actions={
        id !== DEMO_ID && (
          <a href={markdownUrl(id)} download className={buttonVariants({ variant: "ghost", size: "sm" })}>
            <Download aria-hidden />
            Download report
          </a>
        )
      }
    >
      <div className="space-y-10">
        <section className="space-y-5">
          <div className="space-y-3">
            {id === DEMO_ID && (
              <p className="inline-flex rounded-md border px-2 py-0.5 text-xs text-muted-foreground">
                Recorded audit of the demo project
              </p>
            )}
            <h1 className="text-2xl font-semibold tracking-tight text-balance text-foreground sm:text-3xl">{headline}</h1>
            <div className="flex flex-wrap gap-x-5 gap-y-1.5">
              <InputLink icon={GitBranch} label="Repository" url={inputs.repo_url} />
              <InputLink icon={Globe} label="Live site" url={inputs.site_url} />
              <InputLink icon={FileText} label="Privacy policy" url={inputs.policy_url} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Stat value={String(report.findings.length)} label="Findings with evidence" tone={report.findings.length ? "red" : undefined} />
            <Stat value={String(stats.vendors_found ?? report.observations.filter((o) => o.vendor).length)} label="Third parties receiving data" />
            <Stat
              value={String(stats.requests_pre_consent ?? 0)}
              label="Tracker requests before consent"
              tone={stats.requests_pre_consent ? "amber" : undefined}
            />
            <Stat value={String(stats.files_scanned ?? 0)} label="Source files read" />
          </div>
        </section>

        <section className="space-y-4">
          <div className="space-y-1">
            <h2 className="text-base font-medium text-foreground">Result by country and area of law</h2>
            <p className="text-sm text-muted-foreground">
              Select a cell to see the evidence, the provision it relates to, and how to fix it.
            </p>
          </div>
          <Matrix cells={report.matrix} onSelect={setSelected} />
        </section>

        <Tabs defaultValue="findings" className="gap-5">
          <TabsList variant="line" className="w-full justify-start gap-4 border-b">
            <TabsTrigger value="findings" className="flex-none px-0 pb-2.5">
              Findings
              <span className="rounded-full bg-muted px-1.5 text-xs font-normal text-muted-foreground">{findings.length}</span>
            </TabsTrigger>
            <TabsTrigger value="compare" className="flex-none px-0 pb-2.5">
              Policy vs. product
            </TabsTrigger>
          </TabsList>

          <TabsContent value="findings" className="space-y-4">
            <div role="group" aria-label="Filter by severity" className="flex flex-wrap gap-1.5">
              {(["all", ...SEVERITIES] as const).map((value) => {
                const total = value === "all" ? findings.length : findings.filter((f) => f.severity === value).length;
                if (value !== "all" && total === 0) return null;
                const active = severity === value;
                return (
                  <button
                    key={value}
                    type="button"
                    aria-pressed={active}
                    onClick={() => setSeverity(value)}
                    className={cn(
                      "rounded-md border px-2.5 py-1 text-xs transition-colors outline-none focus-visible:ring-3 focus-visible:ring-ring/50",
                      active ? "border-foreground/40 bg-accent text-foreground" : "text-muted-foreground hover:text-foreground",
                    )}
                  >
                    {value === "all" ? "All" : SEVERITY_LABEL[value]} <span className="tabular-nums opacity-70">{total}</span>
                  </button>
                );
              })}
            </div>
            {visible.length > 0 ? (
              <div className="space-y-3">
                {visible.map((finding) => (
                  <FindingCard key={finding.id} finding={finding} />
                ))}
              </div>
            ) : (
              <p className="rounded-xl border border-dashed p-8 text-center text-sm text-muted-foreground">
                No differences were found between the policy and the observed behaviour.
              </p>
            )}
          </TabsContent>

          <TabsContent value="compare">
            <div className="grid gap-6 lg:grid-cols-2">
              <section className="space-y-3">
                <h3 className="text-sm font-medium text-foreground">What the policy says</h3>
                <PolicyClaimsPanel claims={report.claims} />
              </section>
              <section className="space-y-3">
                <h3 className="text-sm font-medium text-foreground">What the product does</h3>
                <ObservationsPanel observations={report.observations} />
              </section>
            </div>
          </TabsContent>
        </Tabs>

        <p className="border-t pt-5 text-xs text-muted-foreground">
          {report.disclaimer}
          {typeof stats.duration_s === "number" && ` Completed in ${Math.round(stats.duration_s)} s.`}
        </p>
      </div>

      <CellSheet report={report} selected={selected} onSelect={setSelected} onClose={() => setSelected(null)} />
    </Shell>
  );
}

export function AuditView({ id }: { id: string }) {
  const audit = useAudit(id);
  if (audit.phase === "done") return <Report id={id} report={audit.report} />;
  if (audit.phase === "error") return <Failed message={audit.message} retry={audit.retry} />;
  return <Running id={id} events={audit.events} skip={audit.skip} />;
}
