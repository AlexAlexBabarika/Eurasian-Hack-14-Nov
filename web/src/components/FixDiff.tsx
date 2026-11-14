import { FileText, Wrench } from "lucide-react";

import { CopyButton } from "@/components/CopyButton";
import type { Fix } from "@/lib/types";

export function FixDiff({ fix }: { fix: Fix }) {
  if (!fix.policy_clause && !fix.code_change) return null;
  return (
    <div className="overflow-hidden rounded-lg border">
      {fix.policy_clause && (
        <div className="border-l-2 border-status-green bg-status-green/[0.06] p-3">
          <div className="mb-1.5 flex items-center justify-between gap-2">
            <p className="flex items-center gap-1.5 text-xs font-medium text-status-green">
              <FileText aria-hidden className="size-3.5" />
              Add to your policy
            </p>
            <CopyButton text={fix.policy_clause} label="Copy clause" />
          </div>
          <p className="text-sm leading-relaxed text-foreground">{fix.policy_clause}</p>
        </div>
      )}
      {fix.code_change && (
        <div className={fix.policy_clause ? "border-t bg-card/60 p-3" : "bg-card/60 p-3"}>
          <div className="mb-1.5 flex items-center justify-between gap-2">
            <p className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
              <Wrench aria-hidden className="size-3.5" />
              Change in code
            </p>
            <CopyButton text={fix.code_change} />
          </div>
          <p className="text-sm leading-relaxed text-foreground/90">{fix.code_change}</p>
        </div>
      )}
    </div>
  );
}
