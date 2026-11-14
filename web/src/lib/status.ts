import type { CellVerdict, Jurisdiction, Severity, Status } from "@/lib/types";
import { JURISDICTIONS } from "@/lib/types";

// Full class names so Tailwind can see them.
export const STATUS_STYLE: Record<Status, { text: string; tint: string; border: string; bar: string; dot: string }> = {
  red: {
    text: "text-status-red",
    tint: "bg-status-red/10",
    border: "border-status-red/35",
    bar: "bg-status-red",
    dot: "bg-status-red",
  },
  amber: {
    text: "text-status-amber",
    tint: "bg-status-amber/10",
    border: "border-status-amber/35",
    bar: "bg-status-amber",
    dot: "bg-status-amber",
  },
  green: {
    text: "text-status-green",
    tint: "bg-status-green/10",
    border: "border-status-green/35",
    bar: "bg-status-green",
    dot: "bg-status-green",
  },
  grey: {
    text: "text-status-grey",
    tint: "bg-status-grey/10",
    border: "border-status-grey/30",
    bar: "bg-status-grey/60",
    dot: "bg-status-grey",
  },
};

export const SEVERITY_STATUS: Record<Severity, Status> = { high: "red", medium: "amber", low: "grey" };

const STATUS_RANK: Record<Status, number> = { red: 0, amber: 1, green: 2, grey: 3 };

export function worstStatus(statuses: Status[]): Status | null {
  return statuses.reduce<Status | null>(
    (worst, status) => (worst === null || STATUS_RANK[status] < STATUS_RANK[worst] ? status : worst),
    null,
  );
}

export function matrixJurisdictions(matrix: CellVerdict[]): Jurisdiction[] {
  return JURISDICTIONS.filter((jurisdiction) => matrix.some((cell) => cell.jurisdiction === jurisdiction));
}

// Worst status of one finding across the cells of each jurisdiction; null where the finding does not apply.
export function findingStatusByJurisdiction(
  matrix: CellVerdict[],
  findingId: string,
): { jurisdiction: Jurisdiction; status: Status | null }[] {
  return matrixJurisdictions(matrix).map((jurisdiction) => ({
    jurisdiction,
    status: worstStatus(
      matrix
        .filter((cell) => cell.jurisdiction === jurisdiction)
        .flatMap((cell) => {
          const status = cell.finding_statuses[findingId] ?? (cell.finding_ids.includes(findingId) ? cell.status : null);
          return status ? [status] : [];
        }),
    ),
  }));
}
