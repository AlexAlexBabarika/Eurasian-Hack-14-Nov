import Link from "next/link";
import { ArrowRight, Check } from "lucide-react";
import { cn } from "cn";

import type { Comparison } from "@/lib/compare";
import { ruleLabel } from "@/lib/labels";

function Figure({ value, label, className }: { value: number; label: string; className?: string }) {
  return (
    <div>
      <dd className={cn("text-2xl font-semibold tracking-tight tabular-nums", className ?? "text-foreground")}>{value}</dd>
      <dt className="text-xs text-muted-foreground">{label}</dt>
    </div>
  );
}

export function BeforeAfter({ comparison, beforeId }: { comparison: Comparison; beforeId: string }) {
  const { resolved, remaining, added, cellsImproved, cellsWorsened, cellsCompared } = comparison;
  return (
    <section aria-labelledby="before-after-title" className="space-y-4 rounded-xl border bg-card p-4 sm:p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <div className="space-y-1">
          <h2 id="before-after-title" className="text-base font-medium text-foreground">
            Before and after
          </h2>
          <p className="text-sm text-muted-foreground">
            Compared with the earlier audit of this product. Cells that changed show their earlier result.
          </p>
        </div>
        <Link
          href={`/audit/${encodeURIComponent(beforeId)}`}
          className="inline-flex items-center gap-1 rounded text-sm text-muted-foreground underline underline-offset-4 outline-none hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50"
        >
          Open the earlier report
          <ArrowRight aria-hidden className="size-3.5" />
        </Link>
      </div>

      <dl className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-4">
        <Figure value={resolved.length} label="Findings resolved" className={resolved.length ? "text-status-green" : undefined} />
        <Figure value={remaining.length} label="Findings remaining" className={remaining.length ? "text-status-amber" : undefined} />
        <Figure value={added.length} label="New findings" className={added.length ? "text-status-red" : undefined} />
        <Figure
          value={cellsImproved}
          label={`of ${cellsCompared} areas improved${cellsWorsened ? `, ${cellsWorsened} got worse` : ""}`}
          className={cellsImproved ? "text-status-green" : undefined}
        />
      </dl>

      {resolved.length > 0 && (
        <div className="space-y-2 border-t pt-4">
          <h3 className="text-xs font-medium tracking-wide text-muted-foreground uppercase">Resolved</h3>
          <ul className="grid gap-x-6 gap-y-1.5 sm:grid-cols-2">
            {resolved.map((finding) => (
              <li key={finding.id} className="flex min-w-0 items-start gap-2 text-sm" title={finding.title}>
                <Check aria-hidden className="mt-0.5 size-4 shrink-0 text-status-green" />
                <span className="min-w-0">
                  <span className="text-foreground">{ruleLabel(finding.rule)}</span>
                  <span className="line-clamp-1 text-xs text-muted-foreground">{finding.title}</span>
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
