import { BUNDLED_AUDIT_IDS, DEMO_FIXED_ID, DEMO_ID, DEMO_PORTFOLIO_ID } from "@/lib/api";
import type { AuditReport, AuditSummary, ProgressEvent, Status } from "@/lib/types";
import demoAudit from "../../../api/data/audits/demo-fixture.json";
import demoFixedAudit from "../../../api/data/audits/demo-fixture-fixed.json";
import demoPortfolioAudit from "../../../api/data/audits/demo-portfolio.json";

export type BundledAudit = { report: AuditReport; events: ProgressEvent[] };

export const BUNDLED_AUDITS: Record<string, BundledAudit | undefined> = {
  [DEMO_PORTFOLIO_ID]: {
    report: demoPortfolioAudit.report as AuditReport,
    events: demoPortfolioAudit.events as ProgressEvent[],
  },
  [DEMO_ID]: { report: demoAudit.report as AuditReport, events: demoAudit.events as ProgressEvent[] },
  [DEMO_FIXED_ID]: { report: demoFixedAudit.report as AuditReport, events: demoFixedAudit.events as ProgressEvent[] },
};

function summarize(id: string, report: AuditReport): AuditSummary {
  const status_counts: Record<Status, number> = { red: 0, amber: 0, green: 0, grey: 0 };
  for (const cell of report.matrix) status_counts[cell.status] += 1;
  const input = (key: string) => {
    const value = report.inputs[key];
    return typeof value === "string" ? value : null;
  };
  return {
    id,
    repo_url: input("repo_url"),
    site_url: input("site_url"),
    policy_url: input("policy_url"),
    findings: report.findings.length,
    vendors: report.observations.filter((observation) => observation.vendor).length,
    status_counts,
  };
}

export const BUNDLED_SUMMARIES: AuditSummary[] = BUNDLED_AUDIT_IDS.flatMap((id) => {
  const audit = BUNDLED_AUDITS[id];
  return audit ? [summarize(id, audit.report)] : [];
});

function isFixture(id: string): boolean {
  return id.startsWith(DEMO_ID);
}

export function sortExamples(audits: AuditSummary[]): AuditSummary[] {
  return [...audits].sort((a, b) => Number(isFixture(a.id)) - Number(isFixture(b.id)) || a.id.localeCompare(b.id));
}

function host(url: string | null): string | null {
  if (!url) return null;
  try {
    return new URL(url).host;
  } catch {
    return url;
  }
}

export function exampleSite(audit: AuditSummary): string | null {
  return host(audit.site_url);
}

export function exampleName(audit: AuditSummary): string {
  if (audit.id === DEMO_PORTFOLIO_ID) return "The Portfolio App";
  if (isFixture(audit.id)) return "Notely (demo product)";
  if (audit.repo_url) {
    try {
      const url = new URL(audit.repo_url);
      const [owner, repo] = url.pathname.split("/").filter(Boolean);
      if (url.hostname === "github.com" && owner && repo) return `${owner}/${repo.replace(/\.git$/, "")}`;
    } catch {}
    return audit.repo_url;
  }
  return host(audit.site_url) ?? audit.id;
}

export function exampleNote(audit: AuditSummary): string | null {
  if (audit.id === DEMO_ID) return "Original policy";
  if (audit.id === DEMO_FIXED_ID) return "After the policy fix";
  return null;
}

export function exampleHref(audit: AuditSummary): string {
  const path = `/audit/${encodeURIComponent(audit.id)}`;
  return audit.id === DEMO_FIXED_ID ? `${path}?before=${DEMO_ID}` : path;
}
