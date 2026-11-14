import { JURISDICTION_LABEL, STATUS_LABEL } from "@/lib/labels";
import { findingStatusByJurisdiction } from "@/lib/status";
import type { CellVerdict, Jurisdiction, Status } from "@/lib/types";

const STATUSES: Status[] = ["red", "amber", "green", "grey"];

// Where a finding applies and how it is rated there, as one plain line:
// "Possible inconsistency in EU, KZ · Needs review in UK".
export function JurisdictionChips({ findingId, matrix }: { findingId: string; matrix: CellVerdict[] }) {
  const items = findingStatusByJurisdiction(matrix, findingId);
  if (items.length === 0) return null;
  const groups: { status: Status | null; jurisdictions: Jurisdiction[] }[] = [...STATUSES, null]
    .map((status) => ({ status, jurisdictions: items.filter((item) => item.status === status).map((item) => item.jurisdiction) }))
    .filter((group) => group.jurisdictions.length > 0);
  return (
    <ul aria-label="Status by jurisdiction" className="flex flex-wrap gap-x-2 text-xs text-muted-foreground">
      {groups.map(({ status, jurisdictions }, i) => (
        <li key={status ?? "none"} className="flex gap-x-2">
          {i > 0 && <span aria-hidden>·</span>}
          <span>
            <span className={status ? "text-foreground/80" : undefined}>{status ? STATUS_LABEL[status].name : "Does not apply"}</span> in{" "}
            {jurisdictions.map((jurisdiction, j) => (
              <span key={jurisdiction}>
                {j > 0 && ", "}
                <abbr title={JURISDICTION_LABEL[jurisdiction].name} className="no-underline">
                  {jurisdiction}
                </abbr>
              </span>
            ))}
          </span>
        </li>
      ))}
    </ul>
  );
}
