import type { CSSProperties } from "react";

import type { Severity, Status } from "@/lib/types";

// Full class names so Tailwind can see them.
export const STATUS_STYLE: Record<Status, { text: string; tint: string; border: string; bar: string; dot: string; tone: string }> = {
  red: {
    text: "text-status-red",
    tint: "bg-status-red/10",
    border: "border-status-red/35",
    bar: "bg-status-red",
    dot: "bg-status-red",
    tone: "tone-red",
  },
  amber: {
    text: "text-status-amber",
    tint: "bg-status-amber/10",
    border: "border-status-amber/35",
    bar: "bg-status-amber",
    dot: "bg-status-amber",
    tone: "tone-amber",
  },
  green: {
    text: "text-status-green",
    tint: "bg-status-green/10",
    border: "border-status-green/35",
    bar: "bg-status-green",
    dot: "bg-status-green",
    tone: "tone-green",
  },
  grey: {
    text: "text-status-grey",
    tint: "bg-status-grey/10",
    border: "border-status-grey/30",
    bar: "bg-status-grey/60",
    dot: "bg-status-grey",
    tone: "tone-grey",
  },
};

export const SEVERITY_STATUS: Record<Severity, Status> = { high: "red", medium: "amber", low: "grey" };

// Colour of the light that follows the cursor over a card of this status (canvas colours, so plain hex).
export const SPOTLIGHT_COLOR: Record<Status, string> = { red: "#ff5a52", amber: "#ffc445", green: "#3fdc8b", grey: "#9aa3b5" };

// Surface of a SpotlightCard: flat fill and edge in the status colour, or the neutral card.
export function spotlightSurface(status: Status | undefined, padding: number | string): CSSProperties {
  const toned = status && status !== "grey";
  return {
    padding,
    borderRadius: 12,
    "--spotlight-card-surface": toned ? "color-mix(in srgb, var(--tone) 15%, var(--card))" : status === "grey" ? "transparent" : "var(--card)",
    "--spotlight-card-border": toned ? "color-mix(in srgb, var(--tone) 55%, transparent)" : status === "grey" ? "transparent" : "var(--border)",
    "--spotlight-card-shadow": "none",
  } as CSSProperties;
}
