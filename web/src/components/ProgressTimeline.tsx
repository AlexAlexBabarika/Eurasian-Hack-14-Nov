import { useState } from "react";
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

// Title of the running screen: what the pipeline is doing right now, in words.
const STEP_NOW: Record<Step, string> = {
  clone: "Cloning the repository",
  manifests: "Reading dependency manifests",
  bearer: "Scanning data flows",
  site_scan: "Loading the live site",
  policy_fetch: "Fetching the privacy policy",
  claims: "Extracting policy claims",
  diff: "Comparing code with the policy",
  law: "Retrieving applicable law",
  verdict: "Writing verdicts",
  done: "Preparing the report",
};

// The step in progress, or the next one to start, plus how many verdict cells are written when the API says so.
export function currentStep(events: ProgressEvent[], cells = DEFAULT_CELLS): { step: Step; title: string; detail: string | null } {
  const latest = latestByStep(events);
  const step = STEPS.find((item) => latest[item]?.status === "running") ?? STEPS.find((item) => !isFinished(latest[item])) ?? "done";
  const event = latest[step];
  const counted = step === "verdict" && event?.status === "running" && typeof event.count === "number";
  return { step, title: STEP_NOW[step], detail: counted ? `${Math.min(event.count ?? 0, cells)} of ${cells} cells` : null };
}

// How much of a step's segment is filled.
function stepFill(step: Step, event: ProgressEvent | undefined, cells: number): number {
  if (isFinished(event)) return 1;
  if (event?.status !== "running") return 0;
  if (step === "verdict" && typeof event.count === "number" && cells > 0) return Math.max(0.04, Math.min(event.count / cells, 0.98));
  return 0.4;
}

export function ProgressTimeline({ events, percent }: { events: ProgressEvent[]; percent: number }) {
  const latest = latestByStep(events);
  const { step: current, title } = currentStep(events);
  const last = events[events.length - 1];

  return (
    <div className="space-y-5">
      <div className="space-y-2.5">
        {/* One segment per step, as wide as its share of a typical run. */}
        <div
          role="progressbar"
          aria-label="Audit progress"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={percent}
          aria-valuetext={`${percent}%, ${title}`}
          className="flex h-1.5 gap-0.5"
        >
          {STEPS.map((step) => {
            const event = latest[step];
            const skipped = event?.status === "skipped";
            return (
              <span
                key={step}
                style={{ flexGrow: STEP_WEIGHT[step] }}
                className={cn("h-full basis-0 overflow-hidden rounded-[2px]", skipped ? "segment-skipped" : "bg-white/10")}
              >
                {!skipped && (
                  <span
                    style={{ transform: `scaleX(${stepFill(step, event, DEFAULT_CELLS)})` }}
                    className={cn(
                      "block h-full origin-left transition-transform duration-500 ease-out motion-reduce:transition-none",
                      event?.status === "error" ? "bg-status-red" : "bg-signal",
                    )}
                  />
                )}
              </span>
            );
          })}
        </div>
        <p aria-live="polite" className="min-h-5 text-sm text-muted-foreground">
          {last ? last.message : "Starting the audit."}
          {last?.status === "error" && " The audit continues without this step."}
        </p>
      </div>

      <ol className="border-t">
        {STEPS.map((step) => {
          const event = latest[step];
          const state: StepState = event?.status ?? "pending";
          return (
            <li key={step} className="flex items-baseline justify-between gap-4 border-b py-2 text-sm">
              <span
                className={cn(
                  "shrink-0",
                  state === "pending" && "text-muted-foreground/70",
                  state === "running" && "font-medium text-signal",
                  (state === "done" || state === "error") && "text-foreground",
                  state === "skipped" && "text-muted-foreground",
                )}
                aria-current={step === current ? "step" : undefined}
              >
                {STEP_LABEL[step]}
                <span className="sr-only">: {STATE_TEXT[state]}</span>
              </span>
              {event && (
                <span
                  className={cn(
                    "min-w-0 text-right text-[13px] break-words tabular-nums",
                    state === "error" ? "text-status-red" : state === "running" ? "text-signal" : "text-muted-foreground",
                  )}
                >
                  {state === "skipped" && "Skipped: "}
                  {state === "error" && "Failed: "}
                  {event.message}
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
