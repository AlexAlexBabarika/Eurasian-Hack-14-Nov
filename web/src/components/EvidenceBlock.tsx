"use client";

import { useEffect, useState } from "react";
import type { Evidence } from "@/lib/api";

const LANG: Record<string, string> = {
  ts: "typescript", tsx: "tsx", js: "javascript", jsx: "jsx", mjs: "javascript", cjs: "javascript",
  py: "python", go: "go", rb: "ruby", json: "json", kt: "kotlin", java: "java", dart: "dart", html: "html",
  yaml: "yaml", yml: "yaml", toml: "toml",
};
const KIND: Record<Evidence["kind"], string> = {
  code: "Code", manifest: "Dependency", network: "Network", cookie: "Cookie", policy_quote: "Policy", bearer: "Bearer",
};

function Snippet({ code, file }: { code: string; file?: string | null }) {
  const [html, setHtml] = useState<string | null>(null);
  useEffect(() => {
    let cancelled = false;
    const lang = LANG[file?.split(".").pop() ?? ""] ?? "text";
    import("shiki")
      .then(({ codeToHtml }) => codeToHtml(code, { lang, theme: "github-dark-default" }))
      .then((out) => !cancelled && setHtml(out))
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [code, file]);
  const cls = "overflow-x-auto rounded-md border bg-[#0d1117] p-3 font-mono text-xs leading-relaxed [&_pre]:!bg-transparent";
  // shiki escapes the source it highlights, so its HTML output is safe to inject.
  return html ? (
    <div className={cls} dangerouslySetInnerHTML={{ __html: html }} />
  ) : (
    <pre className={cls}>{code}</pre>
  );
}

export function EvidenceBlock({ evidence }: { evidence: Evidence }) {
  const e = evidence;
  const isHttp = e.url?.startsWith("http");
  return (
    <div className="space-y-1.5">
      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1 text-xs">
        <span className="rounded border px-1.5 py-0.5 font-mono uppercase tracking-wide text-muted-foreground">
          {KIND[e.kind]}
        </span>
        {e.file && (
          <code className="font-mono text-foreground">
            {e.file}
            {e.line ? `:${e.line}` : ""}
          </code>
        )}
        <span className="text-muted-foreground">{e.summary}</span>
      </div>
      {e.snippet && <Snippet code={e.snippet} file={e.file} />}
      {e.quote && (
        <blockquote className="border-l-2 border-amber-500/60 pl-3 text-sm italic text-foreground/90">
          &ldquo;{e.quote}&rdquo;
        </blockquote>
      )}
      {e.url && !e.file && (
        <p className="break-all font-mono text-xs text-muted-foreground">
          {isHttp ? (
            <a href={e.url} target="_blank" rel="noopener noreferrer" className="underline-offset-2 hover:underline">
              {e.url}
            </a>
          ) : (
            e.url
          )}
        </p>
      )}
    </div>
  );
}
