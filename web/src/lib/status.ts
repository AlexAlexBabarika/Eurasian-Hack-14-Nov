import type { Severity, Status } from "@/lib/types";

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
