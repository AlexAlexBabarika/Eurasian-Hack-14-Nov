"use client";

import { useState } from "react";
import { cn } from "cn";

import { FindingCard } from "@/components/FindingCard";
import { SEVERITY_LABEL, SEVERITY_ORDER } from "@/lib/labels";
import type { CellVerdict, Finding, Severity } from "@/lib/types";

const SEVERITIES: Severity[] = ["high", "medium", "low"];

export function FindingsList({ findings, matrix }: { findings: Finding[]; matrix: CellVerdict[] }) {
  const [severity, setSeverity] = useState<Severity | "all">("all");
  const sorted = [...findings].sort((a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity]);
  const visible = severity === "all" ? sorted : sorted.filter((finding) => finding.severity === severity);

  return (
    <>
      <div role="group" aria-label="Filter by severity" className="flex flex-wrap gap-1.5">
        {(["all", ...SEVERITIES] as const).map((value) => {
          const total = value === "all" ? sorted.length : sorted.filter((f) => f.severity === value).length;
          if (value !== "all" && total === 0) return null;
          const active = severity === value;
          return (
            <button
              key={value}
              type="button"
              aria-pressed={active}
              onClick={() => setSeverity(value)}
              className={cn(
                "rounded-full border px-3 py-1 text-xs transition-colors outline-none focus-visible:ring-3 focus-visible:ring-ring/50",
                active ? "border-paper bg-paper text-paper-ink" : "text-muted-foreground hover:border-white/30 hover:text-foreground",
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
            <FindingCard key={finding.id} finding={finding} matrix={matrix} />
          ))}
        </div>
      ) : (
        <p className="rounded-xl border border-dashed p-8 text-center text-sm text-muted-foreground">
          No differences were found between the policy and the observed behaviour.
        </p>
      )}
    </>
  );
}
