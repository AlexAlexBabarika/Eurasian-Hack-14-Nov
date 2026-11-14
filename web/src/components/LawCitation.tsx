import { BadgeCheck, ExternalLink, TriangleAlert } from "lucide-react";

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import type { Provision } from "@/lib/types";

export function LawCitation({ provision }: { provision: Provision }) {
  return (
    <div className="space-y-1.5 rounded-lg border bg-card/60 p-3">
      <div className="flex flex-wrap items-start justify-between gap-x-3 gap-y-1">
        <p className="text-sm font-medium text-foreground">
          {provision.ref}
          <span className="font-normal text-muted-foreground"> · {provision.title}</span>
        </p>
        {provision.verified ? (
          <span className="inline-flex shrink-0 items-center gap-1 rounded border border-border px-1.5 py-0.5 text-xs text-muted-foreground">
            <BadgeCheck aria-hidden className="size-3 text-status-green" />
            Checked against official text
          </span>
        ) : (
          <Tooltip>
            <TooltipTrigger
              render={
                <span
                  tabIndex={0}
                  className="inline-flex shrink-0 cursor-help items-center gap-1 rounded border border-status-amber/35 bg-status-amber/10 px-1.5 py-0.5 text-xs text-status-amber"
                />
              }
            >
              <TriangleAlert aria-hidden className="size-3" />
              Unverified citation
            </TooltipTrigger>
            <TooltipContent>
              Nobody on the team has checked this reference against the official text yet. Open the link and confirm it
              before relying on it.
            </TooltipContent>
          </Tooltip>
        )}
      </div>
      <p className="text-xs text-muted-foreground">{provision.instrument}</p>
      <p className="text-sm text-foreground/90">{provision.summary}</p>
      <a
        href={provision.official_url}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-1 text-xs font-medium text-foreground underline decoration-border underline-offset-4 hover:decoration-foreground"
      >
        Official text
        <ExternalLink aria-hidden className="size-3" />
      </a>
    </div>
  );
}
