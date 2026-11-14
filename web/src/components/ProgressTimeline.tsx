import { useState } from "react";
import { Check, Circle, LoaderCircle, Minus, X } from "lucide-react";
import { cn } from "cn";

import { STEP_LABEL } from "@/lib/labels";
import type { ProgressEvent, Step } from "@/lib/types";
import { AREAS, JURISDICTIONS, STEPS } from "@/lib/types";

type StepState = ProgressEvent["status"] | "pending";

export function latestByStep(events: ProgressEvent[]): Partial<Record<Step, ProgressEvent>> {
  const latest: Partial<Record<Step, ProgressEvent>> = {};
  for (const event of events) latest[event.step] = event;
  return latest;
}

function StepIcon({ state }: { state: StepState }) {
  const base = "flex size-6 shrink-0 items-center justify-center rounded-full border";
  if (state === "done")
    return (
      <span className={cn(base, "border-status-green/40 bg-status-green/10 text-status-green")}>
        <Check aria-hidden className="size-3.5" />
      </span>
    );
  if (state === "running")
    return (
      <span className={cn(base, "tone-signal animate-pulse-dot border-signal/60 bg-signal/15 text-signal")}>
        <LoaderCircle aria-hidden className="size-3.5 animate-spin" />
      </span>
    );
  if (state === "error")
    return (
      <span className={cn(base, "border-status-red/40 bg-status-red/10 text-status-red")}>
        <X aria-hidden className="size-3.5" />
      </span>
    );
  if (state === "skipped")
    return (
      <span className={cn(base, "text-muted-foreground")}>
        <Minus aria-hidden className="size-3.5" />
      </span>
    );
  return (
    <span className={cn(base, "border-dashed text-muted-foreground/40")}>
      <Circle aria-hidden className="size-2 fill-current" />
    </span>
  );
}

const STATE_TEXT: Record<StepState, string> = {
  pending: "Waiting",
  running: "In progress",
  done: "Done",
  error: "Failed, continuing without it",
  skipped: "Skipped",
};

// Rough share of a typical run spent in each step; writing verdicts takes most of it.
const STEP_WEIGHT: Record<Step, number> = {
  clone: 6,
  manifests: 3,
  bearer: 8,
  site_scan: 8,
  policy_fetch: 3,
  claims: 8,
  diff: 2,
  law: 2,
  verdict: 58,
  done: 2,
};
const TOTAL_WEIGHT = STEPS.reduce((sum, step) => sum + STEP_WEIGHT[step], 0);
// One verdict per jurisdiction and area unless the run says otherwise.
const DEFAULT_CELLS = JURISDICTIONS.length * AREAS.length;

function isFinished(event: ProgressEvent | undefined): boolean {
  return event?.status === "done" || event?.status === "skipped" || event?.status === "error";
}

export function progressPercent(events: ProgressEvent[], cells = DEFAULT_CELLS): { finished: number; percent: number } {
  const latest = latestByStep(events);
  const finished = STEPS.filter((step) => isFinished(latest[step])).length;
  let weight = STEPS.reduce((sum, step) => sum + (isFinished(latest[step]) ? STEP_WEIGHT[step] : 0), 0);
  // While verdicts are written, the API reports how many cells are finished in `count`.
  const verdict = latest.verdict;
  if (verdict?.status === "running" && typeof verdict.count === "number" && cells > 0) {
    weight += STEP_WEIGHT.verdict * Math.min(verdict.count / cells, 0.98);
  }
  const percent = finished === STEPS.length ? 100 : Math.min(99, Math.floor((weight / TOTAL_WEIGHT) * 100));
  return { finished, percent };
}

// The percent shown on screen: it only ever moves forward, even if events arrive out of order.
export function useProgressPercent(events: ProgressEvent[]): { finished: number; percent: number } {
  const progress = progressPercent(events);
  const [highest, setHighest] = useState(progress.percent);
  if (progress.percent > highest) setHighest(progress.percent);
  return { finished: progress.finished, percent: Math.max(progress.percent, highest) };
}

export function ProgressTimeline({ events, percent }: { events: ProgressEvent[]; percent: number }) {
  const latest = latestByStep(events);
  const { finished } = progressPercent(events);

  return (
    <div className="space-y-5">
      <div className="space-y-2">
        <div className="flex items-baseline justify-between text-xs text-muted-foreground">
          <span>
            Step {Math.min(finished + 1, STEPS.length)} of {STEPS.length}
          </span>
          <span className="tabular-nums">{percent}%</span>
        </div>
        <div
          role="progressbar"
          aria-label="Audit progress"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={percent}
          className="h-1.5 overflow-hidden rounded-full bg-muted"
        >
          <div
            className="h-full rounded-full bg-signal transition-[width] duration-500"
            style={{ width: `${percent}%` }}
          />
        </div>
      </div>

      <ol aria-live="polite" className="relative">
        {STEPS.map((step, i) => {
          const event = latest[step];
          const state: StepState = event?.status ?? "pending";
          return (
            <li key={step} className="relative flex gap-3 pb-4 last:pb-0">
              {i < STEPS.length - 1 && <span aria-hidden className="absolute top-6 bottom-0 left-3 w-px bg-border" />}
              <StepIcon state={state} />
              <div className="min-w-0 pt-0.5">
                <p
                  className={cn(
                    "text-sm",
                    state === "pending" ? "text-muted-foreground/70" : "font-medium text-foreground",
                    state === "running" && "text-signal",
                  )}
                >
                  {STEP_LABEL[step]}
                  <span className="sr-only">: {STATE_TEXT[state]}</span>
                </p>
                {event && (
                  <p className={cn("font-mono text-xs", state === "error" ? "text-status-red" : "text-muted-foreground")}>
                    {event.message}
                    {state === "error" && " The audit continues without this step."}
                  </p>
                )}
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
