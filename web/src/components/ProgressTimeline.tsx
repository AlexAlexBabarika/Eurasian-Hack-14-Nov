import type { ProgressEvent } from "@/lib/api";
import { cn } from "@/lib/utils";

const STEPS: { id: ProgressEvent["step"]; label: string }[] = [
  { id: "clone", label: "Fetch repository" },
  { id: "manifests", label: "SDK and dependency scan" },
  { id: "bearer", label: "Bearer data-flow scan" },
  { id: "site_scan", label: "Site scan before consent" },
  { id: "policy_fetch", label: "Fetch privacy policy" },
  { id: "claims", label: "Extract policy claims" },
  { id: "diff", label: "Compare behaviour with claims" },
  { id: "law", label: "Retrieve legal provisions" },
  { id: "verdict", label: "Write verdicts" },
];

const DOT: Record<string, string> = {
  pending: "border-border bg-transparent",
  running: "border-sky-400 bg-sky-400/30 animate-pulse",
  done: "border-emerald-400 bg-emerald-400",
  error: "border-red-400 bg-red-400",
  skipped: "border-muted-foreground bg-muted-foreground/40",
};

export function ProgressTimeline({ events }: { events: ProgressEvent[] }) {
  const latest = new Map(events.map((e) => [e.step, e]));
  return (
    <ol className="space-y-0" aria-live="polite">
      {STEPS.map((step, i) => {
        const event = latest.get(step.id);
        const status = event?.status ?? "pending";
        return (
          <li key={step.id} className="relative flex gap-4 pb-5 last:pb-0">
            {i < STEPS.length - 1 && <span className="absolute left-[5px] top-4 h-full w-px bg-border" />}
            <span className={cn("relative mt-1 size-[11px] shrink-0 rounded-full border", DOT[status])} />
            <div className="min-w-0">
              <p className={cn("text-sm font-medium", status === "pending" && "text-muted-foreground")}>
                {step.label}
                {status === "error" && <span className="ml-2 text-xs text-red-300">failed, continuing</span>}
                {status === "skipped" && <span className="ml-2 text-xs text-muted-foreground">skipped</span>}
              </p>
              {event && <p className="mt-0.5 break-words text-xs text-muted-foreground">{event.message}</p>}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
