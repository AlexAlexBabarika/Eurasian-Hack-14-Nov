"use client";

import { ChevronRight } from "lucide-react";
import { cn } from "cn";

import SpotlightCard from "@/components/reactbits/SpotlightCard";
import { StatusIcon } from "@/components/StatusBadge";
import { AREA_LABEL, JURISDICTION_LABEL, STATUS_LABEL } from "@/lib/labels";
import { previousStatus } from "@/lib/compare";
import { SPOTLIGHT_COLOR, spotlightSurface, STATUS_STYLE } from "@/lib/status";
import type { Area, CellVerdict, Jurisdiction, Status } from "@/lib/types";
import { AREAS, JURISDICTIONS } from "@/lib/types";

export type CellKey = { jurisdiction: Jurisdiction; area: Area };

const LEGEND: Status[] = ["red", "amber", "green", "grey"];

function plural(count: number, word: string) {
  return `${count} ${word}${count === 1 ? "" : "s"}`;
}

function Cell({
  cell,
  was,
  index,
  onSelect,
}: {
  cell: CellVerdict;
  was: Status | null;
  index: number;
  onSelect: (key: CellKey) => void;
}) {
  const style = STATUS_STYLE[cell.status];
  const area = AREA_LABEL[cell.area].name;
  const jurisdiction = JURISDICTION_LABEL[cell.jurisdiction].name;
  const grey = cell.status === "grey";
  return (
    // The wrapper carries the entrance, the hover lift and, for red cells, the travelling arc.
    <div
      style={{ "--i": index } as React.CSSProperties}
      className={cn(
        "animate-power-on rounded-xl transition-transform duration-200 hover:-translate-y-0.5",
        style.tone,
        cell.status === "red" && "arc-border",
        grey && "border border-dashed border-white/15",
      )}
    >
      <SpotlightCard
        spotlightColor={SPOTLIGHT_COLOR[cell.status]}
        intensity={0.26}
        spotlightSize={260}
        borderGlow={1}
        style={spotlightSurface(cell.status, 0)}
        className="h-full"
      >
        <button
          type="button"
          onClick={() => onSelect({ jurisdiction: cell.jurisdiction, area: cell.area })}
          aria-label={`${jurisdiction}, ${area}: ${STATUS_LABEL[cell.status].name}${
            was ? `, previously ${STATUS_LABEL[was].name}` : ""
          }. ${cell.headline}. Open details.`}
          className="group flex h-full min-h-[124px] w-full flex-col gap-2 rounded-xl p-4 text-left outline-none focus-visible:ring-3 focus-visible:ring-ring/70 focus-visible:ring-inset"
        >
          <span className="text-xs font-medium text-muted-foreground lg:hidden">{area}</span>
          <span className={cn("flex items-center gap-1.5 text-sm font-semibold", style.text)}>
            <StatusIcon status={cell.status} />
            {STATUS_LABEL[cell.status].name}
          </span>
          {was && (
            <span className="-mt-1 flex items-center gap-1.5 text-xs text-muted-foreground">
              <span aria-hidden className={cn("size-1.5 shrink-0 rounded-full", STATUS_STYLE[was].dot)} />
              Was: {STATUS_LABEL[was].name}
            </span>
          )}
          <span className={cn("line-clamp-3 text-sm leading-snug", grey ? "text-muted-foreground" : "text-foreground/90")}>
            {cell.headline}
          </span>
          <span className="mt-auto flex items-center justify-between gap-2 text-xs text-muted-foreground">
            <span>
              {cell.finding_ids.length > 0
                ? `${plural(cell.finding_ids.length, "finding")}, ${plural(cell.provision_ids.length, "provision")}`
                : "Why not assessed"}
            </span>
            <ChevronRight
              aria-hidden
              className={cn("size-4 opacity-50 transition group-hover:translate-x-1 group-hover:opacity-100", !grey && style.text)}
            />
          </span>
        </button>
      </SpotlightCard>
    </div>
  );
}

export function Matrix({
  cells,
  previous,
  jurisdictions = JURISDICTIONS,
  onSelect,
}: {
  cells: CellVerdict[];
  previous?: CellVerdict[];
  jurisdictions?: Jurisdiction[];
  onSelect: (key: CellKey) => void;
}) {
  const find = (jurisdiction: Jurisdiction, area: Area) =>
    cells.find((cell) => cell.jurisdiction === jurisdiction && cell.area === area);
  const rows = jurisdictions.filter((jurisdiction) => cells.some((cell) => cell.jurisdiction === jurisdiction));
  const grid = "lg:grid lg:grid-cols-[132px_repeat(4,minmax(0,1fr))] lg:gap-3";

  return (
    <div className="space-y-3">
      <div className={cn("hidden", grid)} aria-hidden>
        <span />
        {AREAS.map((area) => (
          <div key={area} className="px-1">
            <p className="text-[15px] font-semibold tracking-tight text-foreground">{AREA_LABEL[area].name}</p>
            <p className="text-xs text-muted-foreground">{AREA_LABEL[area].hint}</p>
          </div>
        ))}
      </div>

      {rows.map((jurisdiction, row) => (
        <section key={jurisdiction} aria-label={JURISDICTION_LABEL[jurisdiction].name} className={cn("space-y-2 lg:space-y-0", grid)}>
          <div className="flex items-baseline gap-3 pt-3 lg:flex-col lg:gap-1 lg:pt-3">
            <p aria-hidden translate="no" className="font-serif text-4xl leading-none text-paper lg:text-5xl">
              {jurisdiction}
            </p>
            <div>
              <p className="text-sm font-medium text-foreground">{JURISDICTION_LABEL[jurisdiction].name}</p>
              <p className="text-xs text-muted-foreground">{JURISDICTION_LABEL[jurisdiction].laws}</p>
            </div>
          </div>
          <div className="grid gap-2 sm:grid-cols-2 lg:contents">
            {AREAS.map((area, column) => {
              const cell = find(jurisdiction, area);
              return cell ? (
                <Cell key={area} cell={cell} was={previousStatus(previous, cell)} index={row * AREAS.length + column} onSelect={onSelect} />
              ) : (
                <div key={area} className="hidden min-h-[124px] rounded-xl border border-dashed lg:block" />
              );
            })}
          </div>
        </section>
      ))}

      <ul className="flex flex-wrap gap-x-5 gap-y-1 pt-2 text-xs text-muted-foreground">
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
