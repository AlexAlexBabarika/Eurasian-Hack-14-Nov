import type { Finding, Status } from "@/lib/api";
import { EvidenceBlock } from "./EvidenceBlock";
import { StatusBadge } from "./StatusBadge";

const SEVERITY: Record<Finding["severity"], string> = {
  high: "text-red-300",
  medium: "text-amber-300",
  low: "text-muted-foreground",
};

/** `status` is the finding's status in one jurisdiction; omit it outside a matrix cell. */
export function FindingCard({ finding, status }: { finding: Finding; status?: Status }) {
  return (
    <article className="rounded-lg border bg-card p-4">
      <header className="flex flex-wrap items-center gap-2 text-xs">
        <span className="font-mono text-muted-foreground">{finding.id}</span>
        <code className="font-mono text-muted-foreground">{finding.rule}</code>
        {status ? (
          <StatusBadge status={status} />
        ) : (
          <span className={`font-mono uppercase ${SEVERITY[finding.severity]}`}>{finding.severity}</span>
        )}
      </header>
      <h4 className="mt-2 text-sm font-medium leading-snug">{finding.title}</h4>
      <div className="mt-3 space-y-3">
        {finding.evidence.map((e, i) => (
          <EvidenceBlock key={i} evidence={e} />
        ))}
      </div>
    </article>
  );
}
