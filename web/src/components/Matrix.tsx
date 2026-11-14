"use client";

import { useState } from "react";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { AREAS, JURISDICTIONS, type AuditReport, type CellVerdict } from "@/lib/api";
import { cn } from "@/lib/utils";
import { FindingCard } from "./FindingCard";
import { FixDiff } from "./FixDiff";
import { LawCitation } from "./LawCitation";
import { STATUS_STYLE, StatusBadge } from "./StatusBadge";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-3">
      <h3 className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{title}</h3>
      {children}
    </section>
  );
}

function CellDetail({ cell, report }: { cell: CellVerdict; report: AuditReport }) {
  const findings = cell.finding_ids.flatMap((id) => report.findings.find((f) => f.id === id) ?? []);
  const provisions = cell.provision_ids.flatMap((id) => report.provisions[id] ?? []);
  return (
    <div className="space-y-8 px-4 pb-8">
      <p className="text-sm leading-relaxed text-foreground/90">{cell.reasoning}</p>
      {(cell.unverified_notes ?? []).length > 0 && (
        <ul className="space-y-1 rounded-md border border-amber-500/40 bg-amber-500/5 p-3 text-xs text-amber-200">
          {cell.unverified_notes?.map((n) => <li key={n}>{n}</li>)}
        </ul>
      )}
      {provisions.length > 0 && (
        <Section title="Official provisions">
          {provisions.map((p) => (
            <LawCitation key={p.id} provision={p} />
          ))}
        </Section>
      )}
      {findings.length > 0 && (
        <Section title={`Evidence (${findings.length} findings)`}>
          {findings.map((f) => (
            <FindingCard key={f.id} finding={f} status={cell.finding_statuses?.[f.id]} />
          ))}
        </Section>
      )}
      {cell.fixes.length > 0 && (
        <Section title="Suggested fixes">
          {cell.fixes.map((fx, i) => (
            <FixDiff key={i} fix={fx} />
          ))}
        </Section>
      )}
    </div>
  );
}

export function Matrix({ report }: { report: AuditReport }) {
  const [open, setOpen] = useState<CellVerdict | null>(null);
  const [last, setLast] = useState<CellVerdict | null>(null); // keeps content mounted during the close animation
  const rows = JURISDICTIONS.filter((j) => report.matrix.some((c) => c.jurisdiction === j.id));
  const shown = open ?? last;
  const label = (c: CellVerdict) =>
    `${JURISDICTIONS.find((j) => j.id === c.jurisdiction)?.label} / ${AREAS.find((a) => a.id === c.area)?.label}`;

  return (
    <>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[720px] table-fixed border-separate border-spacing-2">
          <thead>
            <tr>
              <th className="w-32" />
              {AREAS.map((a) => (
                <th key={a.id} scope="col" className="pb-1 text-left text-xs font-medium text-muted-foreground">
                  {a.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((j) => (
              <tr key={j.id}>
                <th scope="row" className="text-left align-top">
                  <span className="block font-mono text-sm">{j.id}</span>
                  <span className="block text-xs font-normal text-muted-foreground">{j.label}</span>
                </th>
                {AREAS.map((a) => {
                  const cell = report.matrix.find((c) => c.jurisdiction === j.id && c.area === a.id);
                  if (!cell) return <td key={a.id} />;
                  return (
                    <td key={a.id} className="align-top">
                      <button
                        type="button"
                        onClick={() => {
                          setOpen(cell);
                          setLast(cell);
                        }}
                        className={cn(
                          "flex h-28 w-full flex-col items-start gap-2 rounded-lg border p-3 text-left transition-colors hover:brightness-125 focus-visible:outline-2",
                          STATUS_STYLE[cell.status],
                        )}
                      >
                        <StatusBadge status={cell.status} className="border-current/30 bg-transparent" />
                        <span className="line-clamp-3 text-xs leading-snug text-foreground/90">{cell.headline}</span>
                      </button>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Sheet open={open !== null} onOpenChange={(o) => !o && setOpen(null)}>
        <SheetContent className="w-full gap-0 overflow-y-auto data-[side=right]:w-full data-[side=right]:sm:max-w-2xl">
          {shown && (
            <>
              <SheetHeader>
                <div className="flex items-center gap-2">
                  <StatusBadge status={shown.status} />
                  <span className="text-xs text-muted-foreground">{label(shown)}</span>
                </div>
                <SheetTitle className="pr-8 text-base leading-snug">{shown.headline}</SheetTitle>
                <SheetDescription>Possible inconsistencies for review. Not legal advice.</SheetDescription>
              </SheetHeader>
              <CellDetail cell={shown} report={report} />
            </>
          )}
        </SheetContent>
      </Sheet>
    </>
  );
}
