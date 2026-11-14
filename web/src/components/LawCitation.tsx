import type { Provision } from "@/lib/api";

export function LawCitation({ provision }: { provision: Provision }) {
  const p = provision;
  return (
    <div className="rounded-md border p-3">
      <div className="flex flex-wrap items-center gap-2">
        <a
          href={p.official_url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm font-medium underline decoration-muted-foreground/50 underline-offset-4 hover:decoration-foreground"
        >
          {p.ref}
        </a>
        {!p.verified && (
          <span
            title="A human has not yet checked this reference against the official text"
            className="rounded border border-amber-500/40 bg-amber-500/10 px-1.5 py-0.5 font-mono text-[11px] uppercase tracking-wide text-amber-300"
          >
            Unverified
          </span>
        )}
      </div>
      <p className="mt-0.5 text-xs text-muted-foreground">{p.instrument}</p>
      <p className="mt-2 text-sm">
        <span className="font-medium">{p.title}.</span> <span className="text-foreground/80">{p.summary}</span>
      </p>
    </div>
  );
}
