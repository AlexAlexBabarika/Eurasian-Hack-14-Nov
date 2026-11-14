"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import type { Fix } from "@/lib/api";

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      onClick={async () => {
        await navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
      }}
    >
      {copied ? "Copied" : "Copy"}
    </Button>
  );
}

export function FixDiff({ fix }: { fix: Fix }) {
  return (
    <div className="space-y-3 rounded-md border p-3">
      {fix.policy_clause && (
        <div>
          <div className="flex items-center justify-between gap-2">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Policy clause</p>
            <CopyButton text={fix.policy_clause} />
          </div>
          <p className="mt-2 border-l-2 border-emerald-500/60 bg-emerald-500/5 py-2 pl-3 pr-2 text-sm">
            {fix.policy_clause}
          </p>
        </div>
      )}
      {fix.code_change && (
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Code change</p>
          <p className="mt-2 whitespace-pre-wrap text-sm text-foreground/90">{fix.code_change}</p>
        </div>
      )}
    </div>
  );
}
