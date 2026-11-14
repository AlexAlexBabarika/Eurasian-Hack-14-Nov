"use client";

import { useState } from "react";
import { cn } from "cn";
import { TriangleAlert } from "lucide-react";

import { FindingCard } from "@/components/FindingCard";
import { FixDiff } from "@/components/FixDiff";
import { LawCitation } from "@/components/LawCitation";
import type { CellKey } from "@/components/Matrix";
import { StatusBadge } from "@/components/StatusBadge";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { AREA_LABEL, JURISDICTION_LABEL, SEVERITY_ORDER, STATUS_LABEL, STATUS_ORDER } from "@/lib/labels";
import { STATUS_STYLE } from "@/lib/status";
import type { AuditReport, Finding, Provision } from "@/lib/types";
import { JURISDICTIONS } from "@/lib/types";

const REASONING_PREVIEW = 280;

function Reasoning({ text }: { text: string }) {
  const [expanded, setExpanded] = useState(false);
  const long = text.length > REASONING_PREVIEW;
  return (
    <div className="space-y-1">
      <p className={cn("text-sm leading-relaxed text-foreground/90", long && !expanded && "line-clamp-3")}>{text}</p>
      {long && (
        <button
          type="button"
          aria-expanded={expanded}
          onClick={() => setExpanded((value) => !value)}
          className="rounded text-sm text-muted-foreground underline underline-offset-4 outline-none hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50"
        >
          {expanded ? "Show less" : "Read the full reasoning"}
        </button>
      )}
    </div>
  );
}

export function CellSheet({
  report,
  selected,
  onSelect,
  onClose,
}: {
  report: AuditReport;
  selected: CellKey | null;
  onSelect: (key: CellKey) => void;
  onClose: () => void;
}) {
  const cell = selected
    ? report.matrix.find((c) => c.jurisdiction === selected.jurisdiction && c.area === selected.area)
    : undefined;
  const siblings = selected
    ? JURISDICTIONS.flatMap((j) => report.matrix.filter((c) => c.jurisdiction === j && c.area === selected.area))
    : [];
  const findings = cell
    ? cell.finding_ids
        .map((id) => report.findings.find((finding) => finding.id === id))
        .filter((finding): finding is Finding => Boolean(finding))
        .sort(
          (a, b) =>
            STATUS_ORDER[cell.finding_statuses[a.id] ?? "grey"] - STATUS_ORDER[cell.finding_statuses[b.id] ?? "grey"] ||
            SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity],
        )
    : [];
  const provisions = cell
    ? cell.provision_ids.map((id) => report.provisions[id]).filter((p): p is Provision => Boolean(p))
    : [];
  const fixes = cell ? cell.fixes.filter((fix) => fix.policy_clause || fix.code_change) : [];
  const tabs = [
    { value: "evidence", label: "Evidence", count: findings.length },
    { value: "law", label: "Law", count: provisions.length },
    { value: "fix", label: "How to fix", count: fixes.length },
  ].filter((tab) => tab.count > 0);

  return (
    <Sheet open={Boolean(cell)} onOpenChange={(open) => !open && onClose()}>
      <SheetContent className="gap-0 data-[side=right]:w-full data-[side=right]:sm:max-w-2xl">
        {cell && (
          <>
            <SheetHeader className="gap-3 border-b p-5 pr-12">
              <div className="space-y-1">
                <SheetDescription className="text-xs">{AREA_LABEL[cell.area].name} in</SheetDescription>
                <div role="tablist" aria-label="Jurisdiction" className="flex flex-wrap gap-1.5">
                  {siblings.map((sibling) => {
                    const active = sibling.jurisdiction === cell.jurisdiction;
                    return (
                      <button
                        key={sibling.jurisdiction}
                        type="button"
                        role="tab"
                        aria-selected={active}
                        title={STATUS_LABEL[sibling.status].name}
                        onClick={() => onSelect({ jurisdiction: sibling.jurisdiction, area: sibling.area })}
                        className={cn(
                          "inline-flex items-center gap-2 rounded-md border px-2.5 py-1.5 text-sm transition-colors outline-none focus-visible:ring-3 focus-visible:ring-ring/50",
                          active
                            ? "border-foreground/40 bg-accent text-foreground"
                            : "text-muted-foreground hover:bg-accent/50 hover:text-foreground",
                        )}
                      >
                        <span aria-hidden className={cn("size-2 rounded-full", STATUS_STYLE[sibling.status].dot)} />
                        {JURISDICTION_LABEL[sibling.jurisdiction].name}
                        <span className="sr-only">: {STATUS_LABEL[sibling.status].name}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
              <div className="space-y-2">
                <StatusBadge status={cell.status} />
                <SheetTitle className="text-lg leading-snug">{cell.headline}</SheetTitle>
              </div>
            </SheetHeader>

            <div key={`${cell.jurisdiction}-${cell.area}`} className="flex-1 space-y-5 overflow-y-auto p-5">
              <Reasoning text={cell.reasoning} />

              {tabs.length > 0 && (
                <Tabs defaultValue={tabs[0].value} className="gap-4">
                  <TabsList variant="line" className="w-full justify-start gap-5 border-b">
                    {tabs.map((tab) => (
                      <TabsTrigger key={tab.value} value={tab.value} className="flex-none px-0 pb-2.5">
                        {tab.label}
                        <span className="rounded-full bg-muted px-1.5 text-xs font-normal text-muted-foreground">
                          {tab.count}
                        </span>
                      </TabsTrigger>
                    ))}
                  </TabsList>

                  <TabsContent value="evidence" className="space-y-2.5">
                    {findings.map((finding) => (
                      <FindingCard
                        key={finding.id}
                        finding={finding}
                        status={cell.finding_statuses[finding.id]}
                        showAreas={false}
                      />
                    ))}
                  </TabsContent>

                  <TabsContent value="law" className="space-y-2.5">
                    {cell.unverified_notes.length > 0 && (
                      <div className="flex gap-2.5 rounded-lg border border-status-amber/35 bg-status-amber/10 p-3 text-sm text-foreground/90">
                        <TriangleAlert aria-hidden className="mt-0.5 size-4 shrink-0 text-status-amber" />
                        <div className="space-y-1">
                          {cell.unverified_notes.map((note, i) => (
                            <p key={i}>{note}</p>
                          ))}
                        </div>
                      </div>
                    )}
                    {provisions.map((provision) => (
                      <LawCitation key={provision.id} provision={provision} />
                    ))}
                  </TabsContent>

                  <TabsContent value="fix" className="space-y-2.5">
                    {fixes.map((fix, i) => (
                      <FixDiff key={i} fix={fix} />
                    ))}
                  </TabsContent>
                </Tabs>
              )}

              <p className="border-t pt-4 text-xs text-muted-foreground">{report.disclaimer}</p>
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}
