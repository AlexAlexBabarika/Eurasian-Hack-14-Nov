import type { components } from "./api-types";

type S = components["schemas"];
export type AuditReport = S["AuditReport"];
export type AuditStatus = S["AuditStatus"];
export type AuditRequest = S["AuditRequest"];
export type CellVerdict = S["CellVerdict"];
export type Finding = S["Finding"];
export type Evidence = S["Evidence"];
export type Observation = S["Observation"];
export type Provision = S["Provision"];
export type Fix = S["Fix"];
export type ProgressEvent = S["ProgressEvent"];
export type Status = CellVerdict["status"];
export type Jurisdiction = CellVerdict["jurisdiction"];
export type Area = CellVerdict["area"];

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const JURISDICTIONS: { id: Jurisdiction; label: string }[] = [
  { id: "UK", label: "United Kingdom" },
  { id: "EU", label: "European Union" },
  { id: "KZ", label: "Kazakhstan" },
];
export const AREAS: { id: Area; label: string }[] = [
  { id: "personal_data", label: "Personal data" },
  { id: "ai_transparency", label: "AI transparency" },
  { id: "consumer", label: "Consumer protection" },
  { id: "financial", label: "Financial" },
];

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    const detail = typeof body?.detail === "string" ? body.detail : `Request failed (${res.status})`;
    throw new Error(detail);
  }
  return res.json();
}

export async function createAudit(req: AuditRequest): Promise<{ id: string }> {
  const res = await fetch(`${API_URL}/audits`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(req),
  });
  return json(res);
}

export async function getAudit(id: string): Promise<AuditStatus> {
  return json(await fetch(`${API_URL}/audits/${encodeURIComponent(id)}`));
}

export const eventsUrl = (id: string) => `${API_URL}/audits/${encodeURIComponent(id)}/events`;
export const markdownUrl = (id: string) => `${API_URL}/audits/${encodeURIComponent(id)}/report.md`;
