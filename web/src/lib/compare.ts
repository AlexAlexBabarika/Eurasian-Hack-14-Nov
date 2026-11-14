import type { AuditReport, CellVerdict, Finding, Status } from "@/lib/types";

export type Comparison = {
  resolved: Finding[];
  remaining: Finding[];
  added: Finding[];
  cellsImproved: number;
  cellsWorsened: number;
  cellsCompared: number;
  previousCells: CellVerdict[];
};

const SCORE: Partial<Record<Status, number>> = { red: 0, amber: 1, green: 2 };

export function previousStatus(previous: CellVerdict[] | undefined, cell: CellVerdict): Status | null {
  const match = previous?.find((item) => item.jurisdiction === cell.jurisdiction && item.area === cell.area);
  return match && match.status !== cell.status ? match.status : null;
}

// Finding ids are not stable between audits, so findings are matched by rule.
export function compareReports(before: AuditReport, after: AuditReport): Comparison {
  const rulesBefore = new Set(before.findings.map((finding) => finding.rule));
  const rulesAfter = new Set(after.findings.map((finding) => finding.rule));
  let cellsImproved = 0;
  let cellsWorsened = 0;
  let cellsCompared = 0;
  for (const cell of after.matrix) {
    const earlier = before.matrix.find((item) => item.jurisdiction === cell.jurisdiction && item.area === cell.area);
    if (!earlier) continue;
    cellsCompared += 1;
    const was = SCORE[earlier.status];
    const now = SCORE[cell.status];
    if (was === undefined || now === undefined) continue;
    if (now > was) cellsImproved += 1;
    if (now < was) cellsWorsened += 1;
  }
  return {
    resolved: before.findings.filter((finding) => !rulesAfter.has(finding.rule)),
    remaining: after.findings.filter((finding) => rulesBefore.has(finding.rule)),
    added: after.findings.filter((finding) => !rulesBefore.has(finding.rule)),
    cellsImproved,
    cellsWorsened,
    cellsCompared,
    previousCells: before.matrix,
  };
}
