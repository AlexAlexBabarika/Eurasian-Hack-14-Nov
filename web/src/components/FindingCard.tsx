"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "cn";

import { EvidenceBlock } from "@/components/EvidenceBlock";
import { SeverityBadge, StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { AREA_LABEL, ruleCode, ruleLabel } from "@/lib/labels";
import { SEVERITY_STATUS } from "@/lib/status";
import type { Finding, Status } from "@/lib/types";

const VISIBLE_EVIDENCE = 2;

// `status` is the finding's status in one jurisdiction; it replaces the jurisdiction-neutral severity.
export function FindingCard({
  finding,
  status,
  showAreas = true,
}: {
  finding: Finding;
  status?: Status;
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

  return (
    <article
      className={cn(
        "@container rounded-2xl p-5",
        (status ?? SEVERITY_STATUS[finding.severity]) === "red"
          ? "tone-red tone-wash tone-edge"
          : "border bg-card",
      )}
    >
      <header className="space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          {status ? <StatusBadge status={status} className="px-1.5 py-0.5 text-[11px]" /> : <SeverityBadge severity={finding.severity} />}
          <span className="text-xs text-muted-foreground">
            {ruleLabel(finding.rule)}
            <span className="ml-1.5 font-mono text-muted-foreground/70">{ruleCode(finding.rule)}</span>
          </span>
          {showAreas && (
            <span className="ml-auto flex flex-wrap gap-1">
              {finding.areas.map((area) => (
                <span key={area} className="rounded border px-1.5 py-0.5 text-[11px] text-muted-foreground">
                  {AREA_LABEL[area].name}
                </span>
              ))}
            </span>
          )}
        </div>
        <h3 className="text-lg leading-snug font-semibold tracking-tight text-foreground">{finding.title}</h3>
      </header>

      <div
        className={cn(
          "mt-4 grid gap-4",
          hasPolicy && product.length > 0 && "@2xl:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]",
        )}
      >
        {hasPolicy && (
          <section className="space-y-2">
            <h4 className="font-serif text-lg leading-none text-paper">The policy says</h4>
            {finding.policy_quote && (
              <blockquote className="paper rounded-lg px-4 py-3 font-serif text-[17px] leading-7 shadow-lg shadow-black/30">
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
            <h4 className="mb-2 font-mono text-sm leading-none font-medium text-foreground">The product does</h4>
            <div className="space-y-3">
              {evidence.map((item, i) => (
                <EvidenceBlock key={i} evidence={item} />
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
    </article>
  );
}
