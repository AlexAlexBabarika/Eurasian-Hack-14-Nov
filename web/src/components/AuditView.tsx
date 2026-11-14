"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Download, Plus, TriangleAlert } from "lucide-react";
import { cn } from "cn";

import { BeforeAfter } from "@/components/BeforeAfter";
import { CellSheet } from "@/components/CellSheet";
import { DataFlow } from "@/components/DataFlow";
import { FindingsList } from "@/components/FindingsList";
import type { CellKey } from "@/components/Matrix";
import { Matrix } from "@/components/Matrix";
import { ProgressTimeline } from "@/components/ProgressTimeline";
import { RecheckForm } from "@/components/RecheckForm";
import { ReportInputs } from "@/components/ReportInputs";
import { ObservationsPanel, PolicyClaimsPanel } from "@/components/SaysVsDoes";
import { SiteHeader } from "@/components/SiteHeader";
import { Button, buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { DEMO_ID, isBundledAudit, markdownUrl } from "@/lib/api";
import type { Comparison } from "@/lib/compare";
import { compareReports } from "@/lib/compare";
import { STATUS_STYLE } from "@/lib/status";
import type { AuditReport, Status } from "@/lib/types";
import { useAudit } from "@/lib/useAudit";

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
              {isBundledAudit(id)
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

function Report({
  id,
  report,
  before,
  comparison,
  note,
}: {
  id: string;
  report: AuditReport;
  before?: string;
  comparison?: Comparison | null;
  note?: string;
}) {
  const [selected, setSelected] = useState<CellKey | null>(null);

  const count = (status: Status) => report.matrix.filter((cell) => cell.status === status).length;
  const red = count("red");
  const amber = count("amber");
  const assessed = report.matrix.length - count("grey");
  const vendors = report.observations.filter((observation) => observation.vendor).length;
  const { stats } = report;

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
        !isBundledAudit(id) && (
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
            {isBundledAudit(id) && (
              <p className="inline-flex rounded-md border px-2 py-0.5 text-xs text-muted-foreground">
                Recorded audit of the demo project
              </p>
            )}
            <h1 className="text-2xl font-semibold tracking-tight text-balance text-foreground sm:text-3xl">{headline}</h1>
            <ReportInputs inputs={report.inputs} />
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Stat value={String(report.findings.length)} label="Findings with evidence" tone={report.findings.length ? "red" : undefined} />
            <Stat value={String(stats.vendors_found ?? vendors)} label="Third parties receiving data" />
            <Stat
              value={String(stats.requests_pre_consent ?? 0)}
              label="Tracker requests before consent"
              tone={stats.requests_pre_consent ? "amber" : undefined}
            />
            <Stat value={String(stats.files_scanned ?? 0)} label="Source files read" />
          </div>
        </section>

        {comparison && before && <BeforeAfter comparison={comparison} beforeId={before} />}
        {note && <p className="-mt-4 text-xs text-muted-foreground">{note}</p>}

        <section className="space-y-4">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div className="space-y-1">
              <h2 className="text-base font-medium text-foreground">Result by country and area of law</h2>
              <p className="text-sm text-muted-foreground">
                Select a cell to see the evidence, the provision it relates to, and how to fix it.
              </p>
            </div>
            <RecheckForm id={id} report={report} />
          </div>
          <Matrix cells={report.matrix} previous={comparison?.previousCells} onSelect={setSelected} />
        </section>

        <Tabs defaultValue="findings" className="gap-5">
          <TabsList variant="line" className="w-full justify-start gap-4 border-b">
            <TabsTrigger value="findings" className="flex-none px-0 pb-2.5">
              Findings
              <span className="rounded-full bg-muted px-1.5 text-xs font-normal text-muted-foreground">
                {report.findings.length}
              </span>
            </TabsTrigger>
            <TabsTrigger value="compare" className="flex-none px-0 pb-2.5">
              Policy vs. product
            </TabsTrigger>
            <TabsTrigger value="flows" className="flex-none px-0 pb-2.5">
              Data flows
              <span className="rounded-full bg-muted px-1.5 text-xs font-normal text-muted-foreground">{vendors}</span>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="findings" className="space-y-4">
            <FindingsList findings={report.findings} matrix={report.matrix} />
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

          <TabsContent value="flows">
            <DataFlow report={report} />
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

function ComparedReport({ id, before, report }: { id: string; before: string; report: AuditReport }) {
  const earlier = useAudit(before);
  const earlierReport = earlier.phase === "done" ? earlier.report : null;
  const comparison = useMemo(() => (earlierReport ? compareReports(earlierReport, report) : null), [earlierReport, report]);

  // A recorded audit replays its progress first; the comparison only needs the result.
  useEffect(() => {
    if (earlier.phase === "running") earlier.skip?.();
  }, [earlier]);

  const note =
    earlier.phase === "error"
      ? "The earlier audit could not be loaded, so no comparison is shown."
      : earlier.phase === "running"
        ? "Loading the earlier audit for comparison."
        : undefined;
  return <Report id={id} report={report} before={before} comparison={comparison} note={note} />;
}

export function AuditView({ id, before }: { id: string; before?: string }) {
  const audit = useAudit(id);
  if (audit.phase === "done") {
    return before && before !== id ? (
      <ComparedReport id={id} before={before} report={audit.report} />
    ) : (
      <Report id={id} report={audit.report} />
    );
  }
  if (audit.phase === "error") return <Failed message={audit.message} retry={audit.retry} />;
  return <Running id={id} events={audit.events} skip={audit.skip} />;
}
