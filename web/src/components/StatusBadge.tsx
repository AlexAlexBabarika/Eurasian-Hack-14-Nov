import { CircleAlert, CircleCheck, CircleDashed, TriangleAlert } from "lucide-react";
import { cn } from "cn";

import { SEVERITY_LABEL, STATUS_LABEL } from "@/lib/labels";
import { SEVERITY_STATUS, STATUS_STYLE } from "@/lib/status";
import type { Severity, Status } from "@/lib/types";

const ICON = { red: CircleAlert, amber: TriangleAlert, green: CircleCheck, grey: CircleDashed };

export function StatusIcon({ status, className }: { status: Status; className?: string }) {
  const Icon = ICON[status];
  return <Icon aria-hidden className={cn("size-4 shrink-0", STATUS_STYLE[status].text, className)} />;
}

export function StatusBadge({ status, className }: { status: Status; className?: string }) {
  const style = STATUS_STYLE[status];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-xs font-medium",
        style.tint,
        style.border,
        style.text,
        className,
      )}
    >
      <StatusIcon status={status} className="size-3.5" />
      {STATUS_LABEL[status].name}
    </span>
  );
}

export function SeverityBadge({ severity }: { severity: Severity }) {
  const style = STATUS_STYLE[SEVERITY_STATUS[severity]];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md border px-1.5 py-0.5 text-[11px] font-medium",
        style.tint,
        style.border,
        style.text,
      )}
    >
      <span aria-hidden className={cn("size-1.5 rounded-full", style.dot)} />
      {SEVERITY_LABEL[severity]} severity
    </span>
  );
}
