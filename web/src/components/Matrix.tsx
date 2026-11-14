"use client";

import { ChevronRight } from "lucide-react";
import { cn } from "cn";

import { StatusMark } from "@/components/StatusBadge";
import { AREA_LABEL, JURISDICTION_LABEL, STATUS_LABEL } from "@/lib/labels";
import { previousStatus } from "@/lib/compare";
import { LOUD_STATUS, STATUS_STYLE } from "@/lib/status";
import type { Area, CellVerdict, Jurisdiction, Status } from "@/lib/types";
import { AREAS, JURISDICTIONS } from "@/lib/types";

export type CellKey = { jurisdiction: Jurisdiction; area: Area };

const LEGEND: Status[] = ["red", "amber", "green", "grey"];

function plural(count: number, word: string) {
  return `${count} ${word}${count === 1 ? "" : "s"}`;
}

function footerText(cell: CellVerdict): string {
  if (cell.finding_ids.length > 0)
    return `${plural(cell.finding_ids.length, "finding")}, ${plural(cell.provision_ids.length, "provision")}`;
  if (cell.status === "grey") return "Why not assessed";
  if (cell.status === "green") return "What was checked";
  return "See details";
}

const CELL_TONE: Record<Status, string> = {
  red: "border-status-red/45 bg-[color-mix(in_oklch,var(--status-red)_7%,var(--card))] hover:border-status-red/75",
  amber: "border-status-amber/35 bg-card hover:border-status-amber/65",
  green: "border-border bg-card hover:border-white/25",
  grey: "border-dashed border-white/12 hover:border-white/25",
};

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
  const loud = LOUD_STATUS[cell.status];
  const grey = cell.status === "grey";
  return (
    <button
      type="button"
      style={{ "--i": index } as React.CSSProperties}
      onClick={() => onSelect({ jurisdiction: cell.jurisdiction, area: cell.area })}
      aria-label={`${jurisdiction}, ${area}: ${STATUS_LABEL[cell.status].name}${
        was ? `, previously ${STATUS_LABEL[was].name}` : ""
      }. ${cell.headline}. Open details.`}
      className={cn(
        "animate-cell-in group flex h-full w-full flex-col gap-2 rounded-[10px] border p-3.5 text-left outline-none transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background lg:min-h-[132px]",
        CELL_TONE[cell.status],
      )}
    >
      <span className="text-xs text-muted-foreground lg:hidden">{area}</span>
      <span className={cn("flex items-center gap-1.5 text-[13px]", loud ? cn("font-semibold", style.text) : "font-medium text-muted-foreground")}>
        <StatusMark status={cell.status} className="size-3.5" />
        {STATUS_LABEL[cell.status].name}
      </span>
      {was && (
        <span className="-mt-1 flex items-center gap-1.5 text-xs text-muted-foreground">
          <span aria-hidden className={cn("size-1.5 shrink-0 rounded-full", STATUS_STYLE[was].dot)} />
          Was: {STATUS_LABEL[was].name}
        </span>
      )}
      <span
        className={cn(
          "text-sm leading-snug text-pretty break-words",
          loud ? "text-foreground/90" : "text-muted-foreground",
          grey && "max-lg:hidden",
        )}
      >
        {cell.headline}
      </span>
      <span className="mt-auto flex items-center justify-between gap-2 pt-1 text-xs text-muted-foreground">
        <span>{footerText(cell)}</span>
        <ChevronRight
          aria-hidden
          className="size-3.5 shrink-0 opacity-45 transition group-hover:translate-x-0.5 group-hover:opacity-100 group-focus-visible:opacity-100 motion-reduce:transition-none"
        />
      </span>
    </button>
  );
}

// "8 possible inconsistencies, 1 needs review, 3 not assessed."
export function matrixSummary(cells: CellVerdict[]): string {
  const count = (status: Status) => cells.filter((cell) => cell.status === status).length;
  const parts = [
    count("red") > 0 && `${count("red")} possible ${count("red") === 1 ? "inconsistency" : "inconsistencies"}`,
    count("amber") > 0 && `${count("amber")} ${count("amber") === 1 ? "needs" : "need"} review`,
    count("green") > 0 && `${count("green")} with no issues found`,
    count("grey") > 0 && `${count("grey")} not assessed`,
  ].filter(Boolean);
  return parts.length > 0 ? `${parts.join(", ")}.` : "";
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
  // A column where no country was assessed (financial licensing) gets less room than the ones with content.
  const tracks = AREAS.map((area) =>
    rows.every((jurisdiction) => (find(jurisdiction, area)?.status ?? "grey") === "grey") ? "minmax(0,0.6fr)" : "minmax(0,1fr)",
  ).join(" ");
  const grid = "lg:grid lg:grid-cols-(--matrix-cols) lg:gap-2.5";
  const cols = { "--matrix-cols": `128px ${tracks}` } as React.CSSProperties;

  return (
    <div className="space-y-3">
      <div className={cn("hidden", grid)} style={cols} aria-hidden>
        <span />
        {AREAS.map((area) => (
          <div key={area} className="px-3.5">
            <p className="text-sm font-semibold text-foreground">{AREA_LABEL[area].name}</p>
            <p className="text-xs text-muted-foreground">{AREA_LABEL[area].hint}</p>
          </div>
        ))}
      </div>

      {rows.map((jurisdiction, row) => (
        <section key={jurisdiction} aria-label={JURISDICTION_LABEL[jurisdiction].name} className={cn("space-y-2 lg:space-y-0", grid)} style={cols}>
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
                <div key={area} className="hidden min-h-[132px] rounded-[10px] border border-dashed lg:block" />
              );
            })}
          </div>
        </section>
      ))}

      <ul className="mt-5 flex flex-wrap gap-x-6 gap-y-1.5 border-t pt-4 text-xs text-muted-foreground">
        {LEGEND.map((status) => (
          <li key={status} className="flex items-center gap-1.5">
            <span aria-hidden className={cn("flex shrink-0 items-center", STATUS_STYLE[status].text)}>
              <StatusMark status={status} className="size-3.5" />
            </span>
            <span>
              <span className={cn("font-semibold", LOUD_STATUS[status] ? STATUS_STYLE[status].text : "text-foreground/80")}>
                {STATUS_LABEL[status].name}
              </span>{" "}
              {STATUS_LABEL[status].description}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
