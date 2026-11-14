import { Check, Minus } from "lucide-react";
import { cn } from "cn";

import { EvidenceBlock } from "@/components/EvidenceBlock";
import { dataCategoryLabel, humanize, SHARING_LABEL } from "@/lib/labels";
import type { Observation, PolicyClaims } from "@/lib/types";

function Chip({ children, tone = "default" }: { children: React.ReactNode; tone?: "default" | "amber" | "red" }) {
  return (
    <span
      className={cn(
        "rounded border px-1.5 py-0.5 text-[11px]",
        tone === "default" && "text-muted-foreground",
        tone === "amber" && "border-status-amber/35 bg-status-amber/10 text-status-amber",
        tone === "red" && "border-status-red/35 bg-status-red/10 text-status-red",
      )}
    >
      {children}
    </span>
  );
}

function ClaimRow({ label, value, stated, quote }: { label: string; value: string; stated: boolean; quote?: string }) {
  return (
    <li className="flex gap-3 py-3">
      <span
        className={cn(
          "mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full border",
          stated ? "border-foreground/30 text-foreground" : "border-dashed text-muted-foreground",
        )}
      >
        {stated ? <Check aria-hidden className="size-3" /> : <Minus aria-hidden className="size-3" />}
      </span>
      <div className="min-w-0 space-y-1">
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className={cn("text-sm", stated ? "text-foreground" : "text-muted-foreground")}>{value}</p>
        {quote && (
          <blockquote className="border-l-2 border-paper/50 pl-3 font-serif text-[17px] leading-6 text-paper">&ldquo;{quote}&rdquo;</blockquote>
        )}
      </div>
    </li>
  );
}

function list(values: string[], empty: string, format: (value: string) => string = (v) => v) {
  return values.length ? values.map(format).join(", ") : empty;
}

export function PolicyClaimsPanel({ claims }: { claims: PolicyClaims }) {
  const q = claims.quotes;
  return (
    <ul className="divide-y rounded-xl border bg-card px-4">
      <ClaimRow
        label="Sharing with third parties"
        value={SHARING_LABEL[claims.sharing_statement] ?? humanize(claims.sharing_statement)}
        stated={claims.sharing_statement !== "unclear"}
        quote={q.sharing_statement}
      />
      <ClaimRow
        label="Named service providers"
        value={list(claims.named_processors, "None named")}
        stated={claims.named_processors.length > 0}
        quote={q.named_processors}
      />
      <ClaimRow
        label="Data it says it collects"
        value={list(claims.data_categories, "None listed", dataCategoryLabel)}
        stated={claims.data_categories.length > 0}
        quote={q.data_categories}
      />
      <ClaimRow label="Use of AI" value={claims.mentions_ai ? "Mentioned" : "Not mentioned"} stated={claims.mentions_ai} quote={q.mentions_ai} />
      <ClaimRow
        label="International transfers"
        value={claims.international_transfers ? "Mentioned" : "Not mentioned"}
        stated={claims.international_transfers}
        quote={q.international_transfers}
      />
      <ClaimRow
        label="Retention period"
        value={claims.retention_stated ? "Stated" : "Not stated"}
        stated={claims.retention_stated}
        quote={q.retention_stated}
      />
      <ClaimRow
        label="Rights it lists"
        value={list(claims.rights_listed, "None listed", humanize)}
        stated={claims.rights_listed.length > 0}
        quote={q.rights_listed}
      />
      <ClaimRow
        label="How to delete your data"
        value={claims.deletion_method ?? "Not described"}
        stated={Boolean(claims.deletion_method)}
        quote={q.deletion_method}
      />
      <ClaimRow
        label="Cookie consent"
        value={claims.cookie_consent_described ? "Described" : "Not described"}
        stated={claims.cookie_consent_described}
        quote={q.cookies ?? q.cookie_consent_described}
      />
    </ul>
  );
}

export function ObservationsPanel({ observations }: { observations: Observation[] }) {
  return (
    <div className="space-y-2.5">
      {observations.map((observation) => (
        <details key={observation.id} className="group rounded-xl border bg-card">
          <summary className="flex cursor-pointer list-none flex-wrap items-center gap-x-3 gap-y-2 p-4 outline-none focus-visible:ring-3 focus-visible:ring-ring/50 [&::-webkit-details-marker]:hidden">
            <div className="min-w-[160px]">
              <p className="text-sm font-medium text-foreground">{observation.vendor ?? "Application logs"}</p>
              <p className="text-xs text-muted-foreground">
                {observation.purpose_guess ? humanize(observation.purpose_guess) : "Purpose unknown"}
                {observation.vendor_country && ` · ${observation.vendor_country}`}
              </p>
            </div>
            <div className="flex flex-1 flex-wrap gap-1">
              {observation.data_categories.map((category) => (
                <Chip key={category}>{dataCategoryLabel(category)}</Chip>
              ))}
              {observation.is_ai && <Chip tone="amber">AI service</Chip>}
              {observation.pre_consent && <Chip tone="red">Before consent</Chip>}
            </div>
            <span className="text-xs text-muted-foreground group-open:hidden">
              Show evidence ({observation.evidence.length})
            </span>
            <span className="hidden text-xs text-muted-foreground group-open:inline">Hide evidence</span>
          </summary>
          <div className="space-y-3 border-t p-4">
            {observation.evidence.map((item, i) => (
              <EvidenceBlock key={i} evidence={item} />
            ))}
          </div>
        </details>
      ))}
    </div>
  );
}
