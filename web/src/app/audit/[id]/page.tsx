"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { use, useEffect, useState } from "react";
import { FindingCard } from "@/components/FindingCard";
import { Matrix } from "@/components/Matrix";
import { ProgressTimeline } from "@/components/ProgressTimeline";
import { buttonVariants } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { eventsUrl, getAudit, markdownUrl, type AuditReport, type ProgressEvent } from "@/lib/api";

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="mt-0.5 font-mono text-lg">{value ?? "n/a"}</dd>
    </div>
  );
}

function Report({ report }: { report: AuditReport }) {
  const { inputs, stats, claims } = report;
  const vendors = report.observations.filter((o) => o.vendor);
  const claimRows: [string, string][] = [
    ["Sharing statement", claims.sharing_statement.replaceAll("_", " ")],
    ["Named processors", claims.named_processors.join(", ") || "none"],
    ["Data categories", claims.data_categories.join(", ") || "none"],
    ["Mentions AI", claims.mentions_ai ? "yes" : "no"],
    ["International transfers", claims.international_transfers ? "yes" : "no"],
    ["Retention period stated", claims.retention_stated ? "yes" : "no"],
    ["Rights listed", claims.rights_listed.join(", ") || "none"],
    ["Deletion method", claims.deletion_method ?? "none"],
    ["Cookie consent described", claims.cookie_consent_described ? "yes" : "no"],
  ];
  return (
    <div className="space-y-10">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">Audit report</h1>
          {(["repo_url", "site_url", "policy_url"] as const).map((k) => (
            <p key={k} className="truncate font-mono text-xs text-muted-foreground">
              {String(inputs[k] ?? "")}
            </p>
          ))}
        </div>
        <a href={markdownUrl(report.id)} target="_blank" rel="noopener noreferrer" className={buttonVariants({ variant: "outline" })}>
          Export Markdown
        </a>
      </div>

      <dl className="grid grid-cols-2 gap-6 rounded-lg border p-5 sm:grid-cols-5">
        <Stat label="Files scanned" value={stats.files_scanned as number} />
        <Stat label="Third-party vendors" value={stats.vendors_found as number} />
        <Stat label="Requests before consent" value={stats.requests_pre_consent as number} />
        <Stat label="Findings" value={report.findings.length} />
        <Stat label="Duration" value={`${stats.duration_s}s`} />
      </dl>

      <section className="space-y-3">
        <h2 className="text-sm font-medium">Jurisdiction matrix</h2>
        <Matrix report={report} />
        <p className="text-xs text-muted-foreground">Select a cell for evidence, official provisions and fixes.</p>
      </section>

      <Tabs defaultValue="findings">
        <TabsList>
          <TabsTrigger value="findings">Findings ({report.findings.length})</TabsTrigger>
          <TabsTrigger value="vendors">Vendors ({vendors.length})</TabsTrigger>
          <TabsTrigger value="claims">Policy claims</TabsTrigger>
        </TabsList>
        <TabsContent value="findings" className="mt-4 space-y-3">
          {report.findings.length === 0 && <p className="text-sm text-muted-foreground">No findings.</p>}
          {report.findings.map((f) => (
            <FindingCard key={f.id} finding={f} />
          ))}
        </TabsContent>
        <TabsContent value="vendors" className="mt-4 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs text-muted-foreground">
              <tr className="border-b">
                {["Vendor", "Country", "Purpose", "Data received", "Before consent"].map((h) => (
                  <th key={h} scope="col" className="py-2 pr-4 font-medium">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {vendors.map((o) => (
                <tr key={o.id} className="border-b last:border-0">
                  <td className="py-2 pr-4 font-medium">{o.vendor}</td>
                  <td className="py-2 pr-4 font-mono text-xs">{o.vendor_country ?? "n/a"}</td>
                  <td className="py-2 pr-4 text-muted-foreground">{o.purpose_guess?.replaceAll("_", " ") ?? "n/a"}</td>
                  <td className="py-2 pr-4 font-mono text-xs">{o.data_categories.join(", ")}</td>
                  <td className="py-2 pr-4">{o.pre_consent ? <span className="text-red-300">yes</span> : "no"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </TabsContent>
        <TabsContent value="claims" className="mt-4 space-y-6">
          <dl className="grid gap-x-6 gap-y-3 text-sm sm:grid-cols-[220px_1fr]">
            {claimRows.map(([k, v]) => (
              <div key={k} className="contents">
                <dt className="text-muted-foreground">{k}</dt>
                <dd>{v}</dd>
              </div>
            ))}
          </dl>
          <div className="space-y-2">
            <h3 className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Quotes from the policy</h3>
            {Object.entries(claims.quotes).map(([k, q]) => (
              <blockquote key={k} className="border-l-2 border-amber-500/60 pl-3 text-sm italic">
                &ldquo;{q}&rdquo;
              </blockquote>
            ))}
          </div>
        </TabsContent>
      </Tabs>

      <p className="border-t pt-6 text-xs text-muted-foreground">{report.disclaimer}</p>
    </div>
  );
}

export default function AuditPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const queryClient = useQueryClient();
  const [events, setEvents] = useState<ProgressEvent[]>([]);
  const { data, error } = useQuery({
    queryKey: ["audit", id],
    queryFn: () => getAudit(id),
    refetchInterval: (q) => (q.state.data?.status === "running" ? 2000 : false),
  });
  const running = data?.status === "running";

  useEffect(() => {
    if (!running) return;
    const source = new EventSource(eventsUrl(id));
    const seen: ProgressEvent[] = [];
    source.addEventListener("progress", (e) => {
      seen.push(JSON.parse((e as MessageEvent).data));
      setEvents([...seen]);
    });
    source.addEventListener("end", () => {
      source.close();
      queryClient.invalidateQueries({ queryKey: ["audit", id] });
    });
    source.onerror = () => source.close(); // polling above still picks up the result
    return () => source.close();
  }, [id, running, queryClient]);

  if (error) {
    const offline = error.message === "Failed to fetch";
    return (
      <div className="max-w-xl space-y-4">
        <h1 className="text-xl font-semibold">{offline ? "Cannot reach the API" : "Audit not available"}</h1>
        <p className="text-sm text-muted-foreground">
          {offline ? "Start it with `make api` and reload this page." : error.message}
        </p>
        <Link href="/" className={buttonVariants({ variant: "outline" })}>
          Start a new audit
        </Link>
      </div>
    );
  }
  if (!data) return <p className="text-sm text-muted-foreground">Loading audit</p>;
  if (data.status === "error") {
    return (
      <div className="max-w-xl space-y-4">
        <h1 className="text-xl font-semibold">The audit failed</h1>
        <p className="font-mono text-sm text-red-300">{data.error}</p>
        <Link href="/" className={buttonVariants({ variant: "outline" })}>
          Try again
        </Link>
      </div>
    );
  }
  if (data.report) return <Report report={data.report} />;
  return (
    <div className="max-w-xl space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Audit in progress</h1>
        <p className="mt-1 text-sm text-muted-foreground">Usually under two minutes. This page updates live.</p>
      </div>
      <ProgressTimeline events={events} />
    </div>
  );
}
