"use client";

import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { DEMO_ID, getAudit, subscribeToEvents } from "@/lib/api";
import type { AuditReport, ProgressEvent } from "@/lib/types";
import demoAudit from "../../../api/data/audits/demo-fixture.json";

export type AuditState =
  | { phase: "running"; events: ProgressEvent[]; skip?: () => void }
  | { phase: "done"; events: ProgressEvent[]; report: AuditReport }
  | { phase: "error"; events: ProgressEvent[]; message: string; retry: () => void };

const DEMO_REPORT = demoAudit.report as AuditReport;
const DEMO_EVENTS = demoAudit.events as ProgressEvent[];

function useDemoAudit(enabled: boolean): AuditState {
  const [events, setEvents] = useState<ProgressEvent[]>([]);
  const [finished, setFinished] = useState(false);

  useEffect(() => {
    if (!enabled) return;
    const timers: ReturnType<typeof setTimeout>[] = [];
    let elapsed = 0;
    for (const event of DEMO_EVENTS) {
      elapsed += event.status === "running" ? 250 : 650;
      timers.push(setTimeout(() => setEvents((current) => [...current, event]), elapsed));
    }
    timers.push(setTimeout(() => setFinished(true), elapsed + 500));
    return () => timers.forEach(clearTimeout);
  }, [enabled]);

  if (finished) return { phase: "done", events: DEMO_EVENTS, report: DEMO_REPORT };
  return { phase: "running", events, skip: () => setFinished(true) };
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
  const isDemo = id === DEMO_ID;
  const demo = useDemoAudit(isDemo);
  const live = useLiveAudit(id, !isDemo);
  return isDemo ? demo : live;
}
