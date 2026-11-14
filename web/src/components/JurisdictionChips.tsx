import { cn } from "cn";

import { StatusIcon } from "@/components/StatusBadge";
import { JURISDICTION_LABEL, STATUS_LABEL } from "@/lib/labels";
import { findingStatusByJurisdiction, STATUS_STYLE } from "@/lib/status";
import type { CellVerdict } from "@/lib/types";

export function JurisdictionChips({ findingId, matrix }: { findingId: string; matrix: CellVerdict[] }) {
  const items = findingStatusByJurisdiction(matrix, findingId);
  if (items.length === 0) return null;
  return (
    <ul aria-label="Status by jurisdiction" className="flex flex-wrap items-center gap-1">
      {items.map(({ jurisdiction, status }) => {
        const label = `${JURISDICTION_LABEL[jurisdiction].name}: ${status ? STATUS_LABEL[status].name : "Does not apply"}`;
        const style = status ? STATUS_STYLE[status] : null;
        return (
          <li
            key={jurisdiction}
            title={label}
            className={cn(
              "inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[11px] font-medium",
              style ? [style.tint, style.border, style.text] : "border-dashed text-muted-foreground/70",
            )}
          >
            {status && <StatusIcon status={status} className="size-3" />}
            <span aria-hidden>{jurisdiction}</span>
            {!status && <span aria-hidden className="font-normal">n/a</span>}
            <span className="sr-only">{label}</span>
          </li>
        );
      })}
    </ul>
  );
}
