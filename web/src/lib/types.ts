import type { components } from "./api-types";

type Schemas = components["schemas"];

export type AuditCreated = Schemas["AuditCreated"];
export type AuditReport = Schemas["AuditReport"];
export type AuditRequest = Schemas["AuditRequest"];
export type AuditStatus = Schemas["AuditStatus"];
export type CellVerdict = Schemas["CellVerdict"];
export type Evidence = Schemas["Evidence"];
export type Finding = Schemas["Finding"];
export type Fix = Schemas["Fix"];
export type Observation = Schemas["Observation"];
export type PolicyClaims = Schemas["PolicyClaims"];
export type ProgressEvent = Schemas["ProgressEvent"];
export type Provision = Schemas["Provision"];

export type Jurisdiction = CellVerdict["jurisdiction"];
export type Area = CellVerdict["area"];
export type Status = CellVerdict["status"];
export type Severity = Finding["severity"];
export type EvidenceKind = Evidence["kind"];
export type Step = ProgressEvent["step"];

export const JURISDICTIONS: Jurisdiction[] = ["UK", "EU", "KZ"];
export const AREAS: Area[] = ["personal_data", "ai_transparency", "consumer", "financial"];
export const STEPS: Step[] = [
  "clone",
  "manifests",
  "bearer",
  "site_scan",
  "policy_fetch",
  "claims",
  "diff",
  "law",
  "verdict",
  "done",
];
