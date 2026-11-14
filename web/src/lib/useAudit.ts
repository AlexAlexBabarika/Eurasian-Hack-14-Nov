"use client";

import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { getAudit, isBundledAudit, subscribeToEvents } from "@/lib/api";
import { BUNDLED_AUDITS } from "@/lib/examples";
import type { AuditReport, ProgressEvent } from "@/lib/types";

export type AuditState =
  | { phase: "running"; events: ProgressEvent[]; skip?: () => void }
  | { phase: "done"; events: ProgressEvent[]; report: AuditReport }
  | { phase: "error"; events: ProgressEvent[]; message: string; retry: () => void };

type Replay = { id: string | null; shown: number; finished: boolean };

function useBundledAudit(id: string): AuditState {
  const audit = BUNDLED_AUDITS[id];
  const [replay, setReplay] = useState<Replay>({ id: null, shown: 0, finished: false });

  useEffect(() => {
    if (!audit) return;
    const timers: ReturnType<typeof setTimeout>[] = [];
    let elapsed = 0;
    audit.events.forEach((event, index) => {
      elapsed += event.status === "running" ? 250 : 650;
      timers.push(setTimeout(() => setReplay({ id, shown: index + 1, finished: false }), elapsed));
    });
    timers.push(setTimeout(() => setReplay({ id, shown: audit.events.length, finished: true }), elapsed + 500));
    return () => timers.forEach(clearTimeout);
  }, [id, audit]);

  if (!audit) return { phase: "running", events: [] };
  const current = replay.id === id ? replay : { id, shown: 0, finished: false };
  if (current.finished) return { phase: "done", events: audit.events, report: audit.report };
  return {
    phase: "running",
    events: audit.events.slice(0, current.shown),
    skip: () => setReplay({ id, shown: audit.events.length, finished: true }),
  };
}

function useLiveAudit(id: string, enabled: boolean): AuditState {
  const [events, setEvents] = useState<ProgressEvent[]>([]);
  const query = useQuery({
    queryKey: ["audit", id],
    queryFn: () => getAudit(id),
    enabled,
    // Polling is the fallback when the event stream drops.
    refetchInterval: (q) => (q.state.data?.status === "running" ? 2500 : false),
  });
  const { refetch } = query;
  const running = enabled && (query.data?.status ?? "running") === "running" && !query.isError;

  useEffect(() => {
    if (!running) return;
    return subscribeToEvents(
      id,
      (event) => setEvents((current) => [...current, event]),
      () => void refetch(),
    );
  }, [id, running, refetch]);

  if (query.isError) {
    return { phase: "error", events, message: query.error.message, retry: () => void refetch() };
  }
  if (query.data?.status === "error") {
    return {
      phase: "error",
      events,
      message: query.data.error || "The audit stopped before a report could be written.",
      retry: () => void refetch(),
    };
  }
  if (query.data?.status === "done" && query.data.report) {
    return { phase: "done", events, report: query.data.report };
  }
  return { phase: "running", events };
}

export function useAudit(id: string): AuditState {
  const bundled = isBundledAudit(id);
  const replayed = useBundledAudit(id);
  const live = useLiveAudit(id, !bundled);
  return bundled ? replayed : live;
}
