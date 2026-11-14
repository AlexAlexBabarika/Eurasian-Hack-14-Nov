"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight } from "lucide-react";
import { cn } from "cn";

import { StatusIcon } from "@/components/StatusBadge";
import { Skeleton } from "@/components/ui/skeleton";
import { listExampleAudits } from "@/lib/api";
import { BUNDLED_SUMMARIES, exampleHref, exampleName, exampleNote, exampleSite, sortExamples } from "@/lib/examples";
import { STATUS_LABEL } from "@/lib/labels";
import type { AuditSummary, Status } from "@/lib/types";

const STATUSES: Status[] = ["red", "amber", "green", "grey"];

function plural(count: number, one: string, many: string): string {
  return `${count} ${count === 1 ? one : many}`;
}

function StatusCounts({ counts }: { counts: AuditSummary["status_counts"] }) {
  return (
    <ul className="flex flex-wrap items-center gap-x-3 gap-y-1">
      {STATUSES.filter((status) => (counts[status] ?? 0) > 0).map((status) => (
        <li key={status} className="flex items-center gap-1 text-xs text-foreground/90 tabular-nums">
          <StatusIcon status={status} className="size-3.5" />
          {counts[status]}
          <span className="sr-only">{STATUS_LABEL[status].name.toLowerCase()}</span>
        </li>
      ))}
    </ul>
  );
}

function ExampleCard({ audit }: { audit: AuditSummary }) {
  const site = exampleSite(audit);
  const note = exampleNote(audit);
  return (
    <li className="min-w-0">
      <Link
        href={exampleHref(audit)}
        className="group flex h-full flex-col gap-3 rounded-xl border bg-card p-4 transition-colors outline-none hover:border-foreground/25 focus-visible:ring-3 focus-visible:ring-ring/50"
      >
        <div className="min-w-0 space-y-0.5">
          <p className="flex items-center gap-1.5 text-sm font-medium text-foreground">
            <span className="truncate">{exampleName(audit)}</span>
            <ArrowRight
              aria-hidden
              className="size-3.5 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5"
            />
          </p>
          <p className="truncate text-xs text-muted-foreground">{[note, site].filter(Boolean).join(" · ") || "No live site"}</p>
        </div>
        <p className="text-xs text-muted-foreground">
          {plural(audit.findings, "finding", "findings")} · {plural(audit.vendors, "third party", "third parties")}
        </p>
        <div className="mt-auto border-t pt-3">
          <p className="sr-only">Verdicts across countries and areas of law:</p>
          <StatusCounts counts={audit.status_counts} />
        </div>
      </Link>
    </li>
  );
}

export function ExampleAudits({ className }: { className?: string }) {
  const query = useQuery({ queryKey: ["example-audits"], queryFn: listExampleAudits, retry: false, staleTime: 60_000 });
  const audits = sortExamples(query.data?.length ? query.data : BUNDLED_SUMMARIES);
  const fromApi = Boolean(query.data?.length);

  return (
    <section aria-labelledby="example-audits-title" className={cn("space-y-4", className)}>
      <div className="space-y-1">
        <h2 id="example-audits-title" className="text-base font-medium text-foreground">
          {fromApi || query.isPending ? "Audits of real open-source products" : "Example audits"}
        </h2>
        <p className="text-sm text-muted-foreground">
          Recorded reports you can open right away. Each one shows the verdicts for the twelve combinations of country and
          area of law.
        </p>
      </div>
      {query.isPending ? (
        <div aria-hidden className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }, (_, i) => (
            <Skeleton key={i} className="h-[132px] rounded-xl" />
          ))}
        </div>
      ) : (
        <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {audits.map((audit) => (
            <ExampleCard key={audit.id} audit={audit} />
          ))}
        </ul>
      )}
    </section>
  );
}
