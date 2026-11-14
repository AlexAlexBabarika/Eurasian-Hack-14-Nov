"use client";

import { useEffect, useState } from "react";
import type { HighlighterCore } from "shiki/core";
import { cn } from "cn";

const LANG_BY_EXT: Record<string, string> = {
  ts: "typescript",
  mts: "typescript",
  tsx: "tsx",
  js: "javascript",
  mjs: "javascript",
  cjs: "javascript",
  jsx: "jsx",
  py: "python",
  html: "html",
  json: "json",
  yml: "yaml",
  yaml: "yaml",
  go: "go",
  rb: "ruby",
};
const THEME = "github-dark-default";

let highlighterPromise: Promise<HighlighterCore> | null = null;

function getHighlighter(): Promise<HighlighterCore> {
  highlighterPromise ??= (async () => {
    const [{ createHighlighterCore }, { createJavaScriptRegexEngine }] = await Promise.all([
      import("shiki/core"),
      import("shiki/engine/javascript"),
    ]);
    return createHighlighterCore({
      themes: [import("shiki/themes/github-dark-default.mjs")],
      langs: [
        import("shiki/langs/typescript.mjs"),
        import("shiki/langs/tsx.mjs"),
        import("shiki/langs/javascript.mjs"),
        import("shiki/langs/jsx.mjs"),
        import("shiki/langs/python.mjs"),
        import("shiki/langs/html.mjs"),
        import("shiki/langs/json.mjs"),
        import("shiki/langs/yaml.mjs"),
        import("shiki/langs/go.mjs"),
        import("shiki/langs/ruby.mjs"),
      ],
      engine: createJavaScriptRegexEngine(),
    });
  })();
  return highlighterPromise;
}

type Token = { content: string; color?: string };

// The API sends the target line with up to two lines of context on each side, without line numbers.
function firstLineNumber(line: number, lineCount: number): number {
  return Math.max(1, line - Math.floor(lineCount / 2));
}

export function CodeSnippet({ code, file, line }: { code: string; file?: string | null; line?: number | null }) {
  const lines = code.replace(/\n$/, "").split("\n");
  const ext = file?.split(".").pop()?.toLowerCase() ?? "";
  const lang = LANG_BY_EXT[ext];
  const [tokens, setTokens] = useState<Token[][] | null>(null);

  useEffect(() => {
    if (!lang) return;
    let cancelled = false;
    getHighlighter()
      .then((highlighter) => {
        if (!cancelled) setTokens(highlighter.codeToTokensBase(code.replace(/\n$/, ""), { lang, theme: THEME }));
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [code, lang]);

  const start = line ? firstLineNumber(line, lines.length) : null;

  return (
    <pre className="overflow-x-auto rounded-md border bg-background/60 py-2 font-mono text-xs leading-5">
      <code className="grid min-w-max">
        {lines.map((text, i) => {
          const number = start === null ? null : start + i;
          const isTarget = number !== null && number === line && lines.length > 1;
          return (
            <span key={i} className={cn("flex px-3", isTarget && "bg-status-amber/10 shadow-[inset_2px_0_0_var(--status-amber)]")}>
              {number !== null && (
                <span aria-hidden className="mr-4 w-6 shrink-0 text-right text-muted-foreground/60 select-none">
                  {number}
                </span>
              )}
              <span className="whitespace-pre">
                {tokens?.[i]
                  ? tokens[i].map((token, j) => (
                      <span key={j} style={{ color: token.color }}>
                        {token.content}
                      </span>
                    ))
                  : text || " "}
              </span>
            </span>
          );
        })}
      </code>
    </pre>
  );
}
