import type { Status } from "@/lib/api";
import { cn } from "@/lib/utils";

export const STATUS_STYLE: Record<Status, string> = {
  red: "border-red-500/40 bg-red-500/10 text-red-300",
  amber: "border-amber-500/40 bg-amber-500/10 text-amber-300",
  green: "border-emerald-500/40 bg-emerald-500/10 text-emerald-300",
  grey: "border-border bg-muted/40 text-muted-foreground",
};
export const STATUS_LABEL: Record<Status, string> = {
  red: "Red",
  amber: "Amber",
  green: "Green",
  grey: "Not assessed",
};

export function StatusBadge({ status, className }: { status: Status; className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded border px-1.5 py-0.5 font-mono text-[11px] font-medium uppercase tracking-wide",
        STATUS_STYLE[status],
        className,
      )}
    >
      {STATUS_LABEL[status]}
    </span>
  );
}
