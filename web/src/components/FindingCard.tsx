"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "cn";

import { EvidenceBlock } from "@/components/EvidenceBlock";
import { JurisdictionChips } from "@/components/JurisdictionChips";
import { Button } from "@/components/ui/button";
import { AREA_LABEL, ruleCode, ruleLabel, SEVERITY_LABEL, STATUS_LABEL } from "@/lib/labels";
import { SEVERITY_STATUS } from "@/lib/status";
import type { CellVerdict, Finding, Status } from "@/lib/types";

// The first piece of product evidence is shown with its code, the second as a one-line reference, the rest on demand.
const VISIBLE_EVIDENCE = 2;

// `status` is the finding's status in one jurisdiction; it replaces the jurisdiction-neutral severity.
// `matrix` adds a per-jurisdiction strip for lists that are not scoped to one jurisdiction.
export function FindingCard({
  finding,
  status,
  matrix,
  showAreas = true,
}: {
  finding: Finding;
  status?: Status;
  matrix?: CellVerdict[];
  showAreas?: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  // Policy-side evidence: the quote itself, or a note that the policy is silent on the point.
  const policyNotes = finding.evidence.filter(
    (item) => item.kind === "policy_quote" && (!item.quote || item.quote !== finding.policy_quote),
  );
  const product = finding.evidence.filter((item) => item.kind !== "policy_quote");
  const hasPolicy = Boolean(finding.policy_quote) || policyNotes.length > 0;
  const hidden = product.length - VISIBLE_EVIDENCE;
  const evidence = expanded ? product : product.slice(0, VISIBLE_EVIDENCE);

  const tone = status ?? SEVERITY_STATUS[finding.severity];

  return (
    // Severity sits in a plain gutter beside the finding, so the panel itself stays neutral.
    <article className="@container overflow-hidden rounded-xl border bg-card">
      <div className="grid @2xl:grid-cols-[112px_minmax(0,1fr)]">
        <div className="flex items-baseline gap-2 px-5 pt-4 @2xl:flex-col @2xl:gap-1 @2xl:border-r @2xl:px-4 @2xl:py-5">
          <p
            className={cn(
              "text-xs leading-snug font-semibold",
              tone === "red" ? "text-status-red" : tone === "amber" ? "text-status-amber" : "text-muted-foreground",
            )}
          >
            {status ? STATUS_LABEL[status].name : SEVERITY_LABEL[finding.severity]}
            {!status && <span className="sr-only"> severity</span>}
          </p>
          <p className="text-xs text-muted-foreground tabular-nums">
            <span className="sr-only">Rule </span>
            {ruleCode(finding.rule)}
          </p>
        </div>
        <div className="min-w-0 p-5 pt-2 @2xl:pt-5">
          <header className="space-y-1.5">
            <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 text-xs text-muted-foreground">
              <span>{ruleLabel(finding.rule)}</span>
              {showAreas && <span>{finding.areas.map((area) => AREA_LABEL[area].name).join(", ")}</span>}
            </div>
            <h3 className="text-lg leading-snug font-semibold tracking-tight text-pretty text-foreground">{finding.title}</h3>
            {matrix && <JurisdictionChips findingId={finding.id} matrix={matrix} />}
          </header>

          <div
            className={cn(
              "mt-4 grid gap-4",
              hasPolicy && product.length > 0 && "@2xl:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]",
            )}
          >
            {hasPolicy && (
              <section className="space-y-2">
                <h4 className="text-xs font-medium text-muted-foreground">The policy says</h4>
                {finding.policy_quote && (
                  <blockquote className="paper rounded-md px-4 py-3 font-serif text-[17px] leading-7">
                    <span className="marker">&ldquo;{finding.policy_quote}&rdquo;</span>
                  </blockquote>
                )}
                {policyNotes.map((item, i) =>
                  item.quote ? (
                    <EvidenceBlock key={i} evidence={item} />
                  ) : (
                    <p
                      key={i}
                      className="rounded-md border border-dashed px-3 py-2 text-sm leading-relaxed text-muted-foreground"
                    >
                      {item.summary}
                    </p>
                  ),
                )}
              </section>
            )}
            {product.length > 0 && (
              <section className="min-w-0">
                <h4 className="mb-2 text-xs font-medium text-muted-foreground">The product does</h4>
                <div className="space-y-3">
                  {evidence.map((item, i) => (
                    <EvidenceBlock key={i} evidence={item} compact={!expanded && i > 0} />
                  ))}
                </div>
                {hidden > 0 && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="mt-2 -ml-2 text-muted-foreground"
                    aria-expanded={expanded}
                    onClick={() => setExpanded((value) => !value)}
                  >
                    <ChevronDown aria-hidden className={cn("transition-transform", expanded && "rotate-180")} />
                    {expanded ? "Show less" : `Show ${hidden} more piece${hidden === 1 ? "" : "s"} of evidence`}
                  </Button>
                )}
              </section>
            )}
          </div>
        </div>
      </div>
    </article>
  );
}
