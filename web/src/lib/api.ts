import type { AuditCreated, AuditRequest, AuditStatus, AuditSummary, ProgressEvent } from "@/lib/types";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
// The cached audit of demo/fixture-app. The web app bundles it, so this report opens without the API.
export const DEMO_ID = "demo-fixture";
// The same product audited again after the policy was corrected. Also bundled.
export const DEMO_FIXED_ID = "demo-fixture-fixed";
export const BUNDLED_AUDIT_IDS: readonly string[] = [DEMO_ID, DEMO_FIXED_ID];

export function isBundledAudit(id: string): boolean {
  return BUNDLED_AUDIT_IDS.includes(id);
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly kind: "network" | "http",
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, init);
  } catch {
    throw new ApiError(
      `Cannot reach the audit service at ${API_URL}. Either it is not running, or it refuses requests from this page${
        typeof window === "undefined" ? "" : ` (${window.location.origin})`
      }.`,
      "network",
    );
  }
  if (!res.ok) {
    let detail = "";
    try {
      const body = await res.json();
      detail = typeof body?.detail === "string" ? body.detail : "";
    } catch {}
    throw new ApiError(detail || `The audit service answered with status ${res.status}.`, "http");
  }
  return res.json() as Promise<T>;
}

export function createAudit(body: AuditRequest): Promise<AuditCreated> {
  return request<AuditCreated>("/audits", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function listExampleAudits(): Promise<AuditSummary[]> {
  return request<AuditSummary[]>("/audits");
}

export function getAudit(id: string): Promise<AuditStatus> {
  return request<AuditStatus>(`/audits/${encodeURIComponent(id)}`);
}

export function markdownUrl(id: string): string {
  return `${API_URL}/audits/${encodeURIComponent(id)}/report.md`;
}

// GET /audits/{id}/events sends `progress` events and closes the stream with `end`.
export function subscribeToEvents(
  id: string,
  onEvent: (event: ProgressEvent) => void,
  onEnd: () => void,
): () => void {
  const source = new EventSource(`${API_URL}/audits/${encodeURIComponent(id)}/events`);
  source.addEventListener("progress", (message) => onEvent(JSON.parse(message.data) as ProgressEvent));
  source.addEventListener("end", () => {
    source.close();
    onEnd();
  });
  // A reconnect would replay every event; polling in useAudit picks up the result instead.
  source.onerror = () => source.close();
  return () => source.close();
}
