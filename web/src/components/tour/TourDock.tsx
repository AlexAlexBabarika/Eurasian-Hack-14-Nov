"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useSyncExternalStore } from "react";
import { Check, ChevronDown, ChevronUp, Compass, X } from "lucide-react";

import { TOUR_STEPS, TOUR_STORAGE_KEY } from "@/lib/tour";
import { cn } from "@/lib/utils";

type TourState = { active: boolean; step: number; open: boolean; hintDismissed: boolean };

const IDLE: TourState = { active: false, step: 0, open: true, hintDismissed: false };
const EVENT = "groundtruth-tour-change";
let cachedRaw: string | null | undefined;
let cachedState: TourState = IDLE;

function read(): TourState {
  let raw: string | null = null;
  try {
    raw = window.localStorage.getItem(TOUR_STORAGE_KEY);
  } catch {}
  if (raw !== cachedRaw) {
    cachedRaw = raw;
    try {
      cachedState = raw ? { ...IDLE, ...(JSON.parse(raw) as Partial<TourState>) } : IDLE;
    } catch {
      cachedState = IDLE;
    }
  }
  return cachedState;
}

function write(next: TourState) {
  try {
    window.localStorage.setItem(TOUR_STORAGE_KEY, JSON.stringify(next));
  } catch {}
  window.dispatchEvent(new Event(EVENT));
}

function subscribe(onChange: () => void) {
  window.addEventListener(EVENT, onChange);
  window.addEventListener("storage", onChange);
  return () => {
    window.removeEventListener(EVENT, onChange);
    window.removeEventListener("storage", onChange);
  };
}

function useTour(): TourState {
  return useSyncExternalStore(subscribe, read, () => IDLE);
}

export function startTour() {
  write({ ...read(), active: true, step: 0, open: true });
}

const FOCUS = "outline-none focus-visible:ring-3 focus-visible:ring-ring/50";

function Dock() {
  const tour = useTour();
  const router = useRouter();
  const pathname = usePathname();
  const search = useSearchParams().toString();
  const here = search ? `${pathname}?${search}` : pathname;

  if (!tour.active) {
    // One quiet invitation on the landing page, until it is dismissed.
    if (pathname !== "/" || tour.hintDismissed) return null;
    return (
      <div className="fixed bottom-5 left-1/2 z-40 flex w-max max-w-[calc(100vw-2rem)] -translate-x-1/2 items-center gap-2 rounded-full border border-white/15 bg-card/95 py-2 pr-2 pl-5 text-base font-medium shadow-lg backdrop-blur sm:text-lg">
        <Link href="/tour" className={cn("inline-flex items-center gap-3 rounded-full py-2 text-foreground", FOCUS)}>
          <Compass aria-hidden className="size-6 text-signal" />
          Judging this? Take the guided tour
        </Link>
        <button
          type="button"
          aria-label="Hide the tour invitation"
          onClick={() => write({ ...tour, hintDismissed: true })}
          className={cn("rounded-full p-2.5 text-muted-foreground hover:text-foreground", FOCUS)}
        >
          <X aria-hidden className="size-5" />
        </button>
      </div>
    );
  }

  const index = Math.min(Math.max(tour.step, 0), TOUR_STEPS.length - 1);
  const step = TOUR_STEPS[index];
  const last = index === TOUR_STEPS.length - 1;
  const onPage = here === step.href;
  const go = (to: number) => {
    write({ ...tour, step: to, open: true });
    if (TOUR_STEPS[to].href !== here) router.push(TOUR_STEPS[to].href);
  };

  return (
    // Above the report's side panel (z-50) so the instructions stay readable while it is open.
    <aside
      aria-label="Guided tour"
      className="fixed bottom-4 left-4 z-[60] w-[min(22rem,calc(100vw-2rem))] rounded-xl border border-white/15 bg-card/95 text-sm shadow-2xl backdrop-blur"
    >
      <div className="flex items-center gap-2 px-3 py-2">
        <Compass aria-hidden className="size-4 shrink-0 text-signal" />
        <p className="min-w-0 flex-1 truncate font-medium text-foreground">
          <span className="text-muted-foreground tabular-nums">
            {index + 1}/{TOUR_STEPS.length}
          </span>{" "}
          {step.title}
        </p>
        <button
          type="button"
          aria-expanded={tour.open}
          aria-label={tour.open ? "Collapse the tour" : "Expand the tour"}
          onClick={() => write({ ...tour, open: !tour.open })}
          className={cn("rounded-md p-1 text-muted-foreground hover:text-foreground", FOCUS)}
        >
          {tour.open ? <ChevronDown aria-hidden className="size-4" /> : <ChevronUp aria-hidden className="size-4" />}
        </button>
        <button
          type="button"
          aria-label="End the tour"
          onClick={() => write({ ...tour, active: false, hintDismissed: true })}
          className={cn("rounded-md p-1 text-muted-foreground hover:text-foreground", FOCUS)}
        >
          <X aria-hidden className="size-4" />
        </button>
      </div>

      {tour.open && (
        <div className="space-y-3 border-t border-white/10 px-3 py-3">
          <p className="text-foreground">{step.action}</p>
          <ul className="space-y-1.5 text-[13px] leading-relaxed text-muted-foreground">
            {step.look.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
          <div className="flex items-center justify-end gap-2 pt-1">
            <>
              <button
                type="button"
                disabled={index === 0}
                onClick={() => go(index - 1)}
                className={cn("rounded-md px-2 py-1 text-muted-foreground hover:text-foreground disabled:opacity-40", FOCUS)}
              >
                Back
              </button>
              {!onPage && (
                <Link href={step.href} className={cn("rounded-md px-2 py-1 text-signal hover:underline", FOCUS)}>
                  Go to this page
                </Link>
              )}
              {last ? (
                <button
                  type="button"
                  onClick={() => write({ ...tour, active: false, hintDismissed: true })}
                  className={cn("inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 font-medium text-primary-foreground", FOCUS)}
                >
                  <Check aria-hidden className="size-3.5" />
                  Finish
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => go(index + 1)}
                  className={cn("rounded-md bg-primary px-3 py-1.5 font-medium text-primary-foreground", FOCUS)}
                >
                  Next
                </button>
              )}
            </>
          </div>
        </div>
      )}
    </aside>
  );
}

export function TourDock() {
  // useSearchParams needs a Suspense boundary so static pages can still be prerendered.
  return (
    <Suspense fallback={null}>
      <Dock />
    </Suspense>
  );
}

export function StartTourButton({ className }: { className?: string }) {
  const router = useRouter();
  return (
    <button
      type="button"
      onClick={() => {
        startTour();
        router.push(TOUR_STEPS[0].href);
      }}
      className={cn(
        "inline-flex h-11 items-center gap-2 rounded-xl bg-primary px-5 text-base font-semibold text-primary-foreground",
        FOCUS,
        className,
      )}
    >
      <Compass aria-hidden className="size-4" />
      Start the guided tour
    </button>
  );
}
