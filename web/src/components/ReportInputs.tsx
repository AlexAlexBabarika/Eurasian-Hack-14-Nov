import { ExternalLink, FileText, GitBranch, Globe } from "lucide-react";

import type { AuditReport } from "@/lib/types";

function shortUrl(url: string): string {
  try {
    const parsed = new URL(url);
    const path = parsed.pathname.replace(/\/$/, "");
    return parsed.hostname === "github.com" ? path.slice(1) : `${parsed.host}${path}`;
  } catch {
    return url;
  }
}

function InputLink({ icon: Icon, label, url, empty }: { icon: typeof Globe; label: string; url: unknown; empty: string }) {
  // `inputs` is an untyped dict in the API schema; the repository and the site are optional.
  if (typeof url !== "string" || !/^https?:\/\//.test(url)) {
    return (
      <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground/70">
        <Icon aria-hidden className="size-3.5 shrink-0" />
        {empty}
      </span>
    );
  }
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="group inline-flex max-w-full items-center gap-1.5 rounded-md text-sm text-muted-foreground outline-none hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50"
    >
      <Icon aria-hidden className="size-3.5 shrink-0" />
      <span className="sr-only">{label}:</span>
      <span className="truncate font-mono text-xs">{shortUrl(url)}</span>
      <ExternalLink aria-hidden className="size-3 shrink-0 opacity-0 group-hover:opacity-100" />
    </a>
  );
}

export function ReportInputs({ inputs }: { inputs: AuditReport["inputs"] }) {
  return (
    <div className="flex flex-wrap items-center gap-x-5 gap-y-1.5">
      <InputLink icon={GitBranch} label="Repository" url={inputs.repo_url} empty="No repository given" />
      <InputLink icon={Globe} label="Live site" url={inputs.site_url} empty="No live site given" />
      <InputLink icon={FileText} label="Privacy policy" url={inputs.policy_url} empty="No policy address given" />
    </div>
  );
}
