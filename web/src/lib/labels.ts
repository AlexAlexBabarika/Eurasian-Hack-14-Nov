import type { Area, EvidenceKind, Jurisdiction, Severity, Status, Step } from "@/lib/types";

export const JURISDICTION_LABEL: Record<Jurisdiction, { name: string; laws: string }> = {
  UK: { name: "United Kingdom", laws: "UK GDPR, PECR, DMCC Act" },
  EU: { name: "European Union", laws: "GDPR, ePrivacy, AI Act, UCPD" },
  KZ: { name: "Kazakhstan", laws: "Personal Data Law, AI Law" },
};

export const AREA_LABEL: Record<Area, { name: string; hint: string }> = {
  personal_data: { name: "Personal data", hint: "Recipients, consent, transfers, retention" },
  ai_transparency: { name: "AI transparency", hint: "Telling users that AI is involved" },
  consumer: { name: "Consumer protection", hint: "Misleading statements, account deletion" },
  financial: { name: "Financial licensing", hint: "Not assessed automatically" },
};

export const STATUS_LABEL: Record<Status, { name: string; description: string }> = {
  red: { name: "Possible inconsistency", description: "Evidence contradicts the policy or a cited provision." },
  amber: { name: "Needs review", description: "A gap exists, but the rule is softer or depends on conditions." },
  green: { name: "No issues found", description: "Nothing in the evidence conflicts with the policy." },
  grey: { name: "Not assessed", description: "Not enough evidence, or outside the automated check." },
};

export const SEVERITY_LABEL: Record<Severity, string> = { high: "High", medium: "Medium", low: "Low" };
export const SEVERITY_ORDER: Record<Severity, number> = { high: 0, medium: 1, low: 2 };
export const STATUS_ORDER: Record<Status, number> = { red: 0, amber: 1, green: 2, grey: 3 };

const RULE_LABEL: Record<string, string> = {
  R1: "Undisclosed processor",
  R2: "Sharing contradiction",
  R3: "Undisclosed data category",
  R4: "Undisclosed AI processing",
  R5: "Tracking before consent",
  R6: "Undisclosed transfer",
  R7: "No deletion path",
  R8: "Personal data in logs",
  R9: "No retention period",
};

export function ruleLabel(rule: string): string {
  const code = rule.split("_")[0];
  return RULE_LABEL[code] ?? humanize(rule.replace(/^R\d+_/, ""));
}

export function ruleCode(rule: string): string {
  return rule.split("_")[0];
}

export const EVIDENCE_KIND_LABEL: Record<EvidenceKind, string> = {
  code: "Code",
  manifest: "Dependency",
  network: "Network request",
  cookie: "Cookie",
  policy_quote: "Policy",
  bearer: "Data-flow scan",
};

export const STEP_LABEL: Record<Step, string> = {
  clone: "Clone repository",
  manifests: "Read dependency manifests",
  bearer: "Scan data flows",
  site_scan: "Load live site before consent",
  policy_fetch: "Fetch privacy policy",
  claims: "Extract policy claims",
  diff: "Compare code with policy",
  law: "Retrieve applicable law",
  verdict: "Write verdicts",
  done: "Report ready",
};

const DATA_CATEGORY_LABEL: Record<string, string> = {
  ip: "IP address",
  device_id: "Device ID",
  user_content: "User content",
  email: "Email",
  name: "Name",
  usage: "Usage",
  payment: "Payment",
  location: "Location",
  health: "Health",
  password: "Password",
  phone: "Phone",
};

export function dataCategoryLabel(category: string): string {
  return DATA_CATEGORY_LABEL[category] ?? humanize(category);
}

export function humanize(value: string): string {
  const text = value.replace(/[_-]+/g, " ").trim().toLowerCase();
  return (text.charAt(0).toUpperCase() + text.slice(1)).replace(/\bai\b/gi, "AI");
}

export const SHARING_LABEL: Record<string, string> = {
  no_sharing: "Says data is never shared",
  processors_only: "Says data goes to service providers only",
  sells_or_shares: "Says data is sold or shared",
  unclear: "Unclear",
};
