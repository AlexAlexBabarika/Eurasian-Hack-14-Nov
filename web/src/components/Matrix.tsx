"use client";

import { ChevronRight } from "lucide-react";
import { cn } from "cn";

import { StatusIcon } from "@/components/StatusBadge";
import { AREA_LABEL, JURISDICTION_LABEL, STATUS_LABEL } from "@/lib/labels";
import { STATUS_STYLE } from "@/lib/status";
import type { Area, CellVerdict, Jurisdiction, Status } from "@/lib/types";
import { AREAS, JURISDICTIONS } from "@/lib/types";

export type CellKey = { jurisdiction: Jurisdiction; area: Area };

const LEGEND: Status[] = ["red", "amber", "green", "grey"];

function plural(count: number, word: string) {
  return `${count} ${word}${count === 1 ? "" : "s"}`;
}

function Cell({ cell, onSelect }: { cell: CellVerdict; onSelect: (key: CellKey) => void }) {
  const style = STATUS_STYLE[cell.status];
  const area = AREA_LABEL[cell.area].name;
  const jurisdiction = JURISDICTION_LABEL[cell.jurisdiction].name;
  return (
    <button
      type="button"
      onClick={() => onSelect({ jurisdiction: cell.jurisdiction, area: cell.area })}
      aria-label={`${jurisdiction}, ${area}: ${STATUS_LABEL[cell.status].name}. ${cell.headline}. Open details.`}
      className={cn(
        "group relative flex min-h-[124px] w-full flex-col gap-2 overflow-hidden rounded-lg border bg-card p-3 pl-4 text-left transition-colors outline-none",
        "hover:border-foreground/30 hover:bg-accent/40 focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50",
        cell.status === "grey" && "border-dashed bg-transparent",
      )}
    >
      <span aria-hidden className={cn("absolute inset-y-0 left-0 w-1", style.bar)} />
      <span className="text-xs font-medium text-muted-foreground lg:hidden">{area}</span>
      <span className={cn("flex items-center gap-1.5 text-xs font-medium", style.text)}>
        <StatusIcon status={cell.status} className="size-3.5" />
        {STATUS_LABEL[cell.status].name}
      </span>
      <span
        className={cn(
          "line-clamp-3 text-sm leading-snug",
          cell.status === "grey" ? "text-muted-foreground" : "text-foreground",
        )}
      >
        {cell.headline}
      </span>
      <span className="mt-auto flex items-center justify-between gap-2 text-xs text-muted-foreground">
        <span>
          {cell.finding_ids.length > 0
            ? `${plural(cell.finding_ids.length, "finding")} · ${plural(cell.provision_ids.length, "provision")}`
            : "Why not assessed"}
        </span>
        <ChevronRight
          aria-hidden
          className="size-4 opacity-40 transition group-hover:translate-x-0.5 group-hover:opacity-100"
        />
      </span>
    </button>
  );
}

export function Matrix({
  cells,
  jurisdictions = JURISDICTIONS,
  onSelect,
}: {
  cells: CellVerdict[];
  jurisdictions?: Jurisdiction[];
  onSelect: (key: CellKey) => void;
}) {
  const find = (jurisdiction: Jurisdiction, area: Area) =>
    cells.find((cell) => cell.jurisdiction === jurisdiction && cell.area === area);
  const rows = jurisdictions.filter((jurisdiction) => cells.some((cell) => cell.jurisdiction === jurisdiction));
  const grid = "lg:grid lg:grid-cols-[150px_repeat(4,minmax(0,1fr))] lg:gap-3";

  return (
    <div className="space-y-3">
      <div className={cn("hidden", grid)} aria-hidden>
        <span />
        {AREAS.map((area) => (
          <div key={area} className="px-1">
            <p className="text-sm font-medium text-foreground">{AREA_LABEL[area].name}</p>
            <p className="text-xs text-muted-foreground">{AREA_LABEL[area].hint}</p>
          </div>
        ))}
      </div>

      {rows.map((jurisdiction) => (
        <section key={jurisdiction} aria-label={JURISDICTION_LABEL[jurisdiction].name} className={cn("space-y-2 lg:space-y-0", grid)}>
          <div className="flex items-baseline gap-2 pt-2 lg:flex-col lg:gap-0.5 lg:pt-3">
            <p className="text-sm font-medium text-foreground">{JURISDICTION_LABEL[jurisdiction].name}</p>
            <p className="text-xs text-muted-foreground">{JURISDICTION_LABEL[jurisdiction].laws}</p>
          </div>
          <div className="grid gap-2 sm:grid-cols-2 lg:contents">
            {AREAS.map((area) => {
              const cell = find(jurisdiction, area);
              return cell ? (
                <Cell key={area} cell={cell} onSelect={onSelect} />
              ) : (
                <div key={area} className="hidden min-h-[124px] rounded-lg border border-dashed lg:block" />
              );
            })}
          </div>
        </section>
      ))}

      <ul className="flex flex-wrap gap-x-5 gap-y-1 pt-1 text-xs text-muted-foreground">
        {LEGEND.map((status) => (
          <li key={status} className="flex items-center gap-1.5">
            <StatusIcon status={status} className="size-3.5" />
            <span className="text-foreground/80">{STATUS_LABEL[status].name}:</span>
            {STATUS_LABEL[status].description}
          </li>
        ))}
      </ul>
    </div>
  );
}
