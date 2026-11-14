"use client";

import { useMemo, useState } from "react";
import { Check, Sparkles } from "lucide-react";
import { cn } from "cn";

import type { FlowLink } from "@/lib/dataflow";
import { buildFlow, CATEGORY_HEIGHT, COUNTRY_HEIGHT, ROW_GAP, VENDOR_HEIGHT } from "@/lib/dataflow";
import { matrixJurisdictions } from "@/lib/status";
import type { AuditReport } from "@/lib/types";

type Active = { kind: "category" | "vendor" | "country"; key: string } | null;

function plural(count: number, word: string, many = `${word}s`) {
  return `${count} ${count === 1 ? word : many}`;
}

function Links({ links, height, isLit }: { links: FlowLink[]; height: number; isLit: (link: FlowLink) => boolean | null }) {
  return (
    <svg aria-hidden width="100%" height={height} viewBox={`0 0 100 ${height}`} preserveAspectRatio="none" className="mt-7 block">
      {links.map((link) => {
        const lit = isLit(link);
        return (
          <path
            key={`${link.category ?? ""}-${link.vendor}`}
            d={`M0,${link.y1} C50,${link.y1} 50,${link.y2} 100,${link.y2}`}
            fill="none"
            stroke="currentColor"
            strokeWidth={lit ? 1.5 : 1}
            vectorEffect="non-scaling-stroke"
            className={cn(
              "transition-colors",
              lit === null ? "text-muted-foreground/40" : lit ? "text-foreground/80" : "text-muted-foreground/10",
            )}
          />
        );
      })}
    </svg>
  );
}

function Column({ title, height, children }: { title: string; height: number; children: React.ReactNode }) {
  return (
    <div className="min-w-0">
      <h4 className="h-7 text-xs font-medium tracking-wide text-muted-foreground uppercase">{title}</h4>
      <ul className="flex flex-col justify-center" style={{ height, gap: ROW_GAP }}>
        {children}
      </ul>
    </div>
  );
}

function VendorBadges({ isAi, preConsent }: { isAi: boolean; preConsent: boolean }) {
  return (
    <>
      {isAi && (
        <span className="inline-flex items-center gap-1 rounded border border-status-amber/35 bg-status-amber/10 px-1.5 py-0.5 text-[11px] text-status-amber">
          <Sparkles aria-hidden className="size-3" />
          AI
        </span>
      )}
      {preConsent && (
        <span className="rounded border border-status-red/35 bg-status-red/10 px-1.5 py-0.5 text-[11px] text-status-red">
          Before consent
        </span>
      )}
    </>
  );
}

const NODE = "min-w-0 rounded-lg border bg-card px-3 transition-opacity flex flex-col justify-center";

export function DataFlow({ report }: { report: AuditReport }) {
  const [active, setActive] = useState<Active>(null);
  const jurisdictions = useMemo(() => matrixJurisdictions(report.matrix), [report.matrix]);
  const flow = useMemo(
    () => buildFlow(report.observations, report.claims.named_processors, jurisdictions),
    [report.observations, report.claims.named_processors, jurisdictions],
  );

  if (flow.vendors.length === 0) {
    return (
      <p className="rounded-xl border border-dashed p-8 text-center text-sm text-muted-foreground">
        No third-party vendors were observed, so there are no data flows to show.
      </p>
    );
  }

  const litVendors = new Set(
    flow.vendors
      .filter(
        (vendor) =>
          !active ||
          (active.kind === "vendor" && vendor.key === active.key) ||
          (active.kind === "category" && vendor.categories.includes(active.key)) ||
          (active.kind === "country" && vendor.country === active.key),
      )
      .map((vendor) => vendor.key),
  );
  const isLit = (link: FlowLink) =>
    active
      ? litVendors.has(link.vendor) && (active.kind !== "category" || !link.category || link.category === active.key)
      : null;
  const categoryLit = (key: string) =>
    !active ||
    (active.kind === "category"
      ? active.key === key
      : flow.vendors.some((vendor) => litVendors.has(vendor.key) && vendor.categories.includes(key)));
  const countryLit = (key: string) => flow.vendors.some((vendor) => litVendors.has(vendor.key) && vendor.country === key);
  const hover = (next: Active) => ({
    onMouseEnter: () => setActive(next),
    onMouseLeave: () => setActive(null),
  });
  const hasPolicy = Boolean(report.stats.claims_method);
  const crossBorder = flow.countries.some((country) => country.crossBorder.length > 0);

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        {plural(flow.vendors.length, "vendor")} in {plural(flow.countries.length, "country", "countries")}{" "}
        {flow.vendors.length === 1 ? "receives" : "receive"} {plural(flow.categories.length, "kind")} of data.
        {hasPolicy && crossBorder && !report.claims.international_transfers && " The policy does not mention international transfers."}
      </p>

      <ul className="space-y-2 md:hidden">
        {flow.vendors.map((vendor) => {
          const country = flow.countries.find((item) => item.key === vendor.country);
          return (
            <li key={vendor.key} className="space-y-1.5 rounded-xl border bg-card p-3">
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="text-sm font-medium text-foreground">{vendor.name}</span>
                <VendorBadges isAi={vendor.isAi} preConsent={vendor.preConsent} />
              </div>
              <p className="text-xs text-muted-foreground">
                {vendor.purpose || "Purpose unknown"}
                {hasPolicy && " · "}
                {hasPolicy && (vendor.named ? "Named in policy" : <span className="text-status-amber">Not named in policy</span>)}
              </p>
              <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs">
                <dt className="text-muted-foreground">Receives</dt>
                <dd className="text-foreground/90">
                  {vendor.categories.map((key) => flow.categories.find((c) => c.key === key)?.label ?? key).join(", ")}
                </dd>
                <dt className="text-muted-foreground">Located in</dt>
                <dd className="text-foreground/90">
                  {country?.known ? country.name : "Could not be determined"}
                  {country && country.crossBorder.length > 0 && (
                    <span className="text-status-amber"> · cross-border for {country.crossBorder.join(", ")}</span>
                  )}
                </dd>
              </dl>
            </li>
          );
        })}
      </ul>

      <div className="hidden overflow-x-auto rounded-xl border p-4 md:block">
        <div className="grid min-w-[760px] grid-cols-[minmax(140px,1fr)_minmax(56px,0.7fr)_minmax(270px,1.7fr)_minmax(56px,0.7fr)_minmax(200px,1.2fr)]">
          <Column title="Data" height={flow.height}>
            {flow.categories.map((category) => (
              <li
                key={category.key}
                {...hover({ kind: "category", key: category.key })}
                style={{ height: CATEGORY_HEIGHT }}
                className={cn(NODE, "shrink-0 text-sm text-foreground", !categoryLit(category.key) && "opacity-35")}
              >
                <span className="truncate">{category.label}</span>
              </li>
            ))}
          </Column>

          <Links links={flow.categoryLinks} height={flow.height} isLit={isLit} />

          <Column title="Sent to" height={flow.height}>
            {flow.vendors.map((vendor) => (
              <li
                key={vendor.key}
                tabIndex={0}
                {...hover({ kind: "vendor", key: vendor.key })}
                onFocus={() => setActive({ kind: "vendor", key: vendor.key })}
                onBlur={() => setActive(null)}
                style={{ height: VENDOR_HEIGHT }}
                className={cn(
                  NODE,
                  "shrink-0 gap-0.5 outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50",
                  !litVendors.has(vendor.key) && "opacity-35",
                )}
              >
                <div className="flex items-center gap-1.5">
                  <span className="truncate text-sm font-medium text-foreground">{vendor.name}</span>
                  <span className="ml-auto flex shrink-0 gap-1">
                    <VendorBadges isAi={vendor.isAi} preConsent={vendor.preConsent} />
                  </span>
                </div>
                <p className="flex items-center gap-1 truncate text-xs text-muted-foreground">
                  <span className="truncate">{vendor.purpose || "Purpose unknown"}</span>
                  {hasPolicy && <span aria-hidden>·</span>}
                  {!hasPolicy ? null : vendor.named ? (
                    <span className="inline-flex shrink-0 items-center gap-0.5">
                      <Check aria-hidden className="size-3" />
                      Named in policy
                    </span>
                  ) : (
                    <span className="shrink-0 text-status-amber">Not named in policy</span>
                  )}
                </p>
                <span className="sr-only">
                  Receives {vendor.categories.map((key) => flow.categories.find((c) => c.key === key)?.label ?? key).join(", ")}.
                  Located in {flow.countries.find((country) => country.key === vendor.country)?.name}.
                </span>
              </li>
            ))}
          </Column>

          <Links links={flow.countryLinks} height={flow.height} isLit={isLit} />

          <Column title="Located in" height={flow.height}>
            {flow.countries.map((country) => (
              <li
                key={country.key}
                {...hover({ kind: "country", key: country.key })}
                style={{ height: COUNTRY_HEIGHT }}
                className={cn(NODE, "shrink-0 gap-0.5", !countryLit(country.key) && "opacity-35")}
              >
                <p className="flex items-baseline gap-1.5">
                  <span className="truncate text-sm font-medium text-foreground">{country.name}</span>
                  <span className="shrink-0 text-xs text-muted-foreground">{plural(country.vendors, "vendor")}</span>
                </p>
                <p className={cn("truncate text-xs", country.crossBorder.length > 0 ? "text-status-amber" : "text-muted-foreground")}>
                  {!country.known
                    ? "Location could not be determined"
                    : country.crossBorder.length > 0
                      ? `Cross-border for ${country.crossBorder.join(", ")}`
                      : "Not a cross-border transfer"}
                </p>
              </li>
            ))}
          </Column>
        </div>
      </div>

      <p className="text-xs text-muted-foreground">
        A transfer is cross-border when the vendor is located outside the jurisdiction: outside the UK, outside the EU
        and EEA, or outside Kazakhstan.
        {jurisdictions.includes("KZ") &&
          " Kazakhstan's personal data law expects personal data of its citizens to be stored in Kazakhstan, so vendors located elsewhere deserve a closer look there."}
      </p>
    </div>
  );
}
