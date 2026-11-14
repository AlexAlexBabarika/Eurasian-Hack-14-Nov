// The judge tour. Every number and status below is read from the bundled demo audits, so the
// text stays true when those audits are regenerated.
import { DEMO_FIXED_ID, DEMO_ID } from "@/lib/api";
import { BUNDLED_AUDITS } from "@/lib/examples";
import { AREA_LABEL, JURISDICTION_LABEL, STATUS_LABEL, ruleLabel } from "@/lib/labels";
import type { Area, AuditReport, Jurisdiction, Status } from "@/lib/types";
import { JURISDICTIONS } from "@/lib/types";

export type TourStep = {
  id: string;
  title: string;
  /** Page the step happens on. */
  href: string;
  /** What to click. */
  action: string;
  /** What appears, and why it matters. */
  look: string[];
};

export const TOUR_STORAGE_KEY = "proveryai-tour";

const before = BUNDLED_AUDITS[DEMO_ID]?.report;
const after = BUNDLED_AUDITS[DEMO_FIXED_ID]?.report;

function cellStatus(report: AuditReport | undefined, jurisdiction: Jurisdiction, area: Area): Status | undefined {
  return report?.matrix.find((cell) => cell.jurisdiction === jurisdiction && cell.area === area)?.status;
}

function cellName(jurisdiction: Jurisdiction, area: Area): string {
  return `${JURISDICTION_LABEL[jurisdiction].name} / ${AREA_LABEL[area].name}`;
}

function statusName(status: Status | undefined): string {
  return status ? `"${STATUS_LABEL[status].name}"` : "not shown";
}

/** How one rule is rated in each country's personal-data cell, e.g. `United Kingdom: "Needs review"`. */
function ruleByCountry(report: AuditReport | undefined, code: string): string {
  const finding = report?.findings.find((item) => item.rule.startsWith(code));
  return JURISDICTIONS.map((jurisdiction) => {
    const cell = report?.matrix.find((item) => item.jurisdiction === jurisdiction && item.area === "personal_data");
    const status = finding ? cell?.finding_statuses?.[finding.id] : undefined;
    return `${JURISDICTION_LABEL[jurisdiction].name}: ${statusName(status)}`;
  }).join(", ");
}

function provisionRefs(report: AuditReport | undefined, jurisdiction: Jurisdiction, area: Area): string {
  const cell = report?.matrix.find((item) => item.jurisdiction === jurisdiction && item.area === area);
  const refs = (cell?.provision_ids ?? []).flatMap((id) => report?.provisions[id]?.ref ?? []);
  return refs.length ? refs.join(" and ") : "the cited provisions";
}

const findingsBefore = before?.findings.length ?? 0;
const findingsAfter = after?.findings.length ?? 0;
const remaining = (after?.findings ?? []).map((finding) => ruleLabel(finding.rule).toLowerCase()).join(" and ");
const assessed = (before?.matrix ?? []).filter((cell) => cell.status !== "grey").length;
const red = (before?.matrix ?? []).filter((cell) => cell.status === "red").length;

export const TOUR_STEPS: TourStep[] = [
  {
    id: "inputs",
    title: "What goes in",
    href: "/",
    action: 'Look at the "Start an audit" form. Do not submit it yet.',
    look: [
      "An audit takes a GitHub repository, a live site and a privacy policy. The repository and the policy are optional.",
      "Scroll down to the recorded audits. They open without the audit service running.",
    ],
  },
  {
    id: "replay",
    title: "Watch an audit run",
    href: `/audit/${DEMO_ID}`,
    action: 'Watch the steps tick, or press "Skip to the report".',
    look: [
      "This replays a recorded audit of Notely, a small demo product we wrote with planted problems.",
      "Each step is a real stage: read the code, load the site before and after the cookie choice, read the policy, compare, map to law.",
    ],
  },
  {
    id: "matrix",
    title: "One verdict per country and area of law",
    href: `/audit/${DEMO_ID}`,
    action: "Read the large number, then the grid under it.",
    look: [
      `${red} of ${assessed} assessed areas show a possible inconsistency. Rows are countries, columns are areas of law.`,
      `Financial licensing is ${statusName("grey")} in every row: it cannot be judged from code, and the report says so instead of guessing.`,
    ],
  },
  {
    id: "cell",
    title: "Evidence, law and fix for one cell",
    href: `/audit/${DEMO_ID}`,
    action: `Click the ${cellName("EU", "personal_data")} cell. In the panel, open "Evidence", then "Law", then "How to fix".`,
    look: [
      "Evidence puts the policy sentence next to the file and line that contradicts it.",
      "Law links each provision to its official text. How to fix gives a policy clause you can copy.",
      "The country buttons at the top of the panel switch to the same area in another country.",
      "Press Esc to close the panel before you press Next.",
    ],
  },
  {
    id: "contrast",
    title: "Same evidence, different law",
    href: `/audit/${DEMO_ID}`,
    action: `In the "Findings" tab, find "${ruleLabel("R5_TRACKING_BEFORE_CONSENT")}" and read its country markers.`,
    look: [
      `The same trackers are rated differently by country. ${ruleByCountry(before, "R5")}.`,
      "UK law now has an exception for statistics-only analytics; EU law has none. That difference comes from the law, not from the model.",
    ],
  },
  {
    id: "kz-ai",
    title: "Kazakhstan's AI law",
    href: `/audit/${DEMO_ID}`,
    action: `Click the ${cellName("KZ", "ai_transparency")} cell and open "Law".`,
    look: [
      `The product sends chat text to an AI provider and the policy never mentions AI. The cell is ${statusName(cellStatus(before, "KZ", "ai_transparency"))} and cites ${provisionRefs(before, "KZ", "ai_transparency")} of Kazakhstan's AI law.`,
      `The same finding in the ${cellName("UK", "ai_transparency")} cell is ${statusName(cellStatus(before, "UK", "ai_transparency"))}: the UK has guidance but no AI statute.`,
      "Press Esc to close the panel before you press Next.",
    ],
  },
  {
    id: "tabs",
    title: "Policy against product, and where data goes",
    href: `/audit/${DEMO_ID}`,
    action: 'Open the "Policy vs. product" tab, then the "Data flows" tab.',
    look: [
      "Policy vs. product lists what the policy claims on one side and what the scan observed on the other.",
      "Data flows traces each kind of data to the company that receives it and the country that company is in.",
    ],
  },
  {
    id: "fixed",
    title: "Fix the policy, run it again",
    href: `/audit/${DEMO_FIXED_ID}?before=${DEMO_ID}`,
    action: 'Press "Skip to the report" if the replay is running. Read the "Before and after" box, then the "Was:" lines inside the grid cells.',
    look: [
      `This is the same product with a corrected policy. Findings go from ${findingsBefore} to ${findingsAfter}.`,
      `What remains (${remaining}) needs a code change, which a policy edit cannot fix. The tool does not let wording hide behaviour.`,
      '"Re-check with an updated policy" above the grid starts this comparison for any report.',
    ],
  },
  {
    id: "live",
    title: "Run your own",
    href: "/",
    action: "Paste a public GitHub repository, its site and its privacy policy, then run the audit.",
    look: [
      "A live audit needs the audit service running and takes about a minute.",
      'A finished live report has "Download report" in the header, which saves it as Markdown.',
    ],
  },
];
