"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Download, Plus, TriangleAlert } from "lucide-react";
import { cn } from "cn";

import { BeforeAfter } from "@/components/BeforeAfter";
import { CellSheet } from "@/components/CellSheet";
import { CountUp } from "@/components/CountUp";
import { DataFlow } from "@/components/DataFlow";
import { FindingsList } from "@/components/FindingsList";
import type { CellKey } from "@/components/Matrix";
import { Matrix } from "@/components/Matrix";
import { latestByStep, progressPercent, ProgressTimeline } from "@/components/ProgressTimeline";
import { RecheckForm } from "@/components/RecheckForm";
import { ReportInputs } from "@/components/ReportInputs";
import LetterGlitch from "@/components/reactbits/LetterGlitch";
import SpotlightCard from "@/components/reactbits/SpotlightCard";
import { ObservationsPanel, PolicyClaimsPanel } from "@/components/SaysVsDoes";
import { SiteHeader } from "@/components/SiteHeader";
import { Button, buttonVariants } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { DEMO_ID, isBundledAudit, markdownUrl } from "@/lib/api";
import type { Comparison } from "@/lib/compare";
import { compareReports } from "@/lib/compare";
import { STEP_LABEL } from "@/lib/labels";
import { SPOTLIGHT_COLOR, spotlightSurface, STATUS_STYLE } from "@/lib/status";
import type { AuditReport, Status } from "@/lib/types";
import { STEPS } from "@/lib/types";
import { useAudit } from "@/lib/useAudit";

// `stats` is an untyped dict in the API schema.
function num(value: unknown, fallback = 0): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function Stat({ value, label, tone, index }: { value: number; label: string; tone?: Status; index: number }) {
  return (
    <div style={{ "--i": index } as React.CSSProperties} className={cn("animate-rise", tone && STATUS_STYLE[tone].tone)}>
      <SpotlightCard
        spotlightColor={tone ? SPOTLIGHT_COLOR[tone] : "#f4efe2"}
        intensity={0.26}
        spotlightSize={220}
        borderGlow={1}
        style={spotlightSurface(tone, "12px 16px")}
        className="h-full"
      >
        <p
          className={cn(
            "text-3xl leading-none font-semibold tracking-tighter tabular-nums",
            tone ? STATUS_STYLE[tone].text : "text-foreground",
          )}
        >
          <CountUp value={value} />
        </p>
        <p className="mt-1.5 text-xs text-muted-foreground">{label}</p>
      </SpotlightCard>
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
          {/* Icon only on phones, so the header never grows wider than the screen. */}
          <span className="sr-only sm:not-sr-only">New audit</span>
        </Link>
      </SiteHeader>
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-8 sm:px-6">{children}</main>
    </div>
  );
}

type Events = Parameters<typeof ProgressTimeline>[0]["events"];

// What the pipeline has reported so far, printed like a terminal session.
function ScanConsole({ events }: { events: Events }) {
  const latest = latestByStep(events);
  const lines = STEPS.filter((step) => latest[step]).map((step) => latest[step]!);
  return (
    <div className="relative min-h-[420px] overflow-hidden rounded-2xl border border-white/10 bg-ink">
      <LetterGlitch
        aria-hidden
        glitchColors={["#5db8ff", "#f4efe2"]}
        baseOpacity={0.2}
        glitchAmount={0.5}
        centerFade={0.2}
        interactive={false}
        clickEffect="none"
        className="absolute inset-0 size-full"
      />
      <ol aria-hidden className="relative space-y-2 p-5 font-mono text-[13px] leading-5 sm:p-6">
        {lines.map((event) => (
          <li key={event.step} className="animate-rise flex gap-3">
            <span
              className={cn(
                "w-4 shrink-0",
                event.status === "done" && "text-status-green",
                event.status === "running" && "text-signal",
                event.status === "error" && "text-status-red",
                event.status === "skipped" && "text-muted-foreground",
              )}
            >
              {event.status === "done" ? "✓" : event.status === "error" ? "×" : event.status === "skipped" ? "–" : ">"}
            </span>
            <span className="min-w-0">
              <span className="text-muted-foreground">{STEP_LABEL[event.step].toLowerCase()}</span>
              <span className="block break-words text-foreground">{event.message}</span>
            </span>
          </li>
        ))}
        <li className="flex gap-3 text-signal">
          <span className="w-4 shrink-0">{">"}</span>
          <span className="animate-caret inline-block h-5 w-2 bg-signal" />
        </li>
      </ol>
    </div>
  );
}

function Running({ id, events, skip }: { id: string; events: Events; skip?: () => void }) {
  const { percent } = progressPercent(events);
  return (
    <Shell>
      <div className="grid gap-8 lg:grid-cols-[minmax(0,400px)_minmax(0,1fr)] lg:gap-12">
        <section className="space-y-6">
          <div className="space-y-2">
            <p aria-hidden className="text-7xl leading-none font-semibold tracking-tighter text-signal tabular-nums">
              {percent}
              <span className="text-3xl text-signal/60">%</span>
            </p>
            <h1 className="text-2xl font-semibold tracking-tight text-foreground">
              Audit in progress…
            </h1>
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
        <section className="hidden space-y-3 lg:block">
          <ScanConsole events={events} />
          <p className="text-xs text-muted-foreground">The results matrix appears here when the audit finishes.</p>
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

  // The count leads the headline; the rest of the sentence follows it.
  const lead = red > 0 ? { count: red, tone: "red" as const } : amber > 0 ? { count: amber, tone: "amber" as const } : null;
  const headline = lead
    ? lead.tone === "red"
      ? `of ${assessed} assessed areas show a possible inconsistency`
      : `of ${assessed} assessed areas need review`
    : assessed > 0
      ? "No issues found in the assessed areas"
      : "Nothing could be assessed";

  return (
    <Shell
      actions={
        !isBundledAudit(id) && (
          <a href={markdownUrl(id)} download className={buttonVariants({ variant: "ghost", size: "sm" })}>
            <Download aria-hidden />
            <span className="sr-only sm:not-sr-only">Download report</span>
          </a>
        )
      }
    >
      <div className="space-y-8">
        <section className="grid grid-cols-[minmax(0,1fr)] items-end gap-x-10 gap-y-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,400px)]">
          <div className="min-w-0 space-y-4">
            {isBundledAudit(id) && (
              <p className="inline-flex rounded-full border border-white/15 px-2.5 py-0.5 text-xs text-muted-foreground">
                Recorded audit of the demo project
              </p>
            )}
            <h1
              aria-label={lead ? `${lead.count} ${headline}` : headline}
              className="flex flex-wrap items-end gap-x-5 gap-y-2 text-foreground"
            >
              {lead && (
                <span
                  className={cn(
                    "text-[clamp(5.5rem,13vw,10rem)] leading-[0.78] font-semibold tracking-tighter tabular-nums",
                    STATUS_STYLE[lead.tone].text,
                  )}
                >
                  <CountUp value={lead.count} duration={1100} />
                </span>
              )}{" "}
              <span className="max-w-md text-[clamp(1.6rem,3vw,2.5rem)] leading-[1.05] font-semibold tracking-tight text-balance">
                {headline}
              </span>
            </h1>
            <ReportInputs inputs={report.inputs} />
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-2">
            <Stat index={0} value={report.findings.length} label="Findings with evidence" tone={report.findings.length ? "red" : undefined} />
            <Stat index={1} value={num(stats.vendors_found, vendors)} label="Third parties receiving data" />
            <Stat
              index={2}
              value={num(stats.requests_pre_consent)}
              label="Tracker requests before consent"
              tone={stats.requests_pre_consent ? "amber" : undefined}
            />
            <Stat index={3} value={num(stats.files_scanned)} label="Source files read" />
          </div>
        </section>

        {comparison && before && <BeforeAfter comparison={comparison} beforeId={before} />}
        {note && <p className="-mt-4 text-xs text-muted-foreground">{note}</p>}

        <section className="space-y-4">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div className="space-y-1">
              <h2 className="text-2xl font-semibold tracking-tight text-foreground">Result by country and area of law</h2>
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
                <h3 className="font-serif text-2xl text-paper">What the policy says</h3>
                <PolicyClaimsPanel claims={report.claims} />
              </section>
              <section className="space-y-3">
                <h3 className="font-mono text-lg font-medium text-foreground">What the product does</h3>
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
