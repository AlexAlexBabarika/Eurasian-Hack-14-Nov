import { Cookie, FileCode2, Globe, Package, Quote, ScanSearch } from "lucide-react";
import type { ReactNode } from "react";

import { CodeSnippet } from "@/components/CodeSnippet";
import { EVIDENCE_KIND_LABEL } from "@/lib/labels";
import type { Evidence, EvidenceKind } from "@/lib/types";

const ICON: Record<EvidenceKind, typeof Globe> = {
  code: FileCode2,
  manifest: Package,
  network: Globe,
  cookie: Cookie,
  policy_quote: Quote,
  bearer: ScanSearch,
};

// Renders `backticked` fragments as inline code.
export function InlineText({ text }: { text: string }): ReactNode {
  return text.split(/(`[^`]+`)/g).map((part, i) =>
    part.startsWith("`") && part.endsWith("`") && part.length > 2 ? (
      <code key={i} className="rounded bg-muted px-1 py-0.5 font-mono text-[0.85em]">
        {part.slice(1, -1)}
      </code>
    ) : (
      part
    ),
  );
}

// `compact` keeps the summary and location and leaves the code or quote for the expanded view.
export function EvidenceBlock({ evidence, compact = false }: { evidence: Evidence; compact?: boolean }) {
  const Icon = ICON[evidence.kind];
  const location = evidence.file ? `${evidence.file}${evidence.line ? `:${evidence.line}` : ""}` : null;

  return (
    <div className="space-y-2">
      <div className="flex items-start gap-2.5">
        <Icon aria-hidden className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
        <div className="min-w-0 space-y-0.5">
          <p className="text-sm text-foreground">
            <InlineText text={evidence.summary} />
          </p>
          <p className="flex flex-wrap items-center gap-x-2 text-xs text-muted-foreground">
            <span>{EVIDENCE_KIND_LABEL[evidence.kind]}</span>
            {location && <span className="font-mono text-foreground/80">{location}</span>}
            {!location && evidence.url && (
              <span className="font-mono break-all text-foreground/80">{evidence.url}</span>
            )}
          </p>
        </div>
      </div>
      {!compact && evidence.snippet && (
        <div className="pl-[26px]">
          <CodeSnippet code={evidence.snippet} file={evidence.file} line={evidence.line} />
        </div>
      )}
      {!compact && evidence.quote && (
        <blockquote className="ml-[26px] border-l-2 border-paper/50 pl-3 font-serif text-[17px] leading-6 text-paper">
          &ldquo;{evidence.quote}&rdquo;
        </blockquote>
      )}
    </div>
  );
}
