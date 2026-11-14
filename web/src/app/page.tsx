"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { JURISDICTIONS, createAudit, type Jurisdiction } from "@/lib/api";
import { cn } from "@/lib/utils";

const DEMO = {
  repo_url: "https://github.com/AlexAlexBabarika/Eurasian-Hack-14-Nov/tree/main/demo/fixture-app",
  site_url: "http://localhost:4100/public/index.html",
  policy_url: "http://localhost:4100/privacy.html",
};
const FIELDS = [
  { name: "repo_url", label: "GitHub repository", placeholder: "https://github.com/acme/app" },
  { name: "site_url", label: "Live site", placeholder: "https://acme.com" },
  { name: "policy_url", label: "Privacy policy", placeholder: "https://acme.com/privacy" },
] as const;

export default function Home() {
  const router = useRouter();
  const [form, setForm] = useState({ repo_url: "", site_url: "", policy_url: "" });
  const [jurisdictions, setJurisdictions] = useState<Jurisdiction[]>(["UK", "EU", "KZ"]);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setPending(true);
    try {
      const { id } = await createAudit({ ...form, jurisdictions });
      router.push(`/audit/${id}`);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error";
      setError(message === "Failed to fetch" ? "Cannot reach the API. Is it running on port 8000?" : message);
      setPending(false);
    }
  }

  const toggle = (j: Jurisdiction) =>
    setJurisdictions((cur) => (cur.includes(j) ? cur.filter((x) => x !== j) : [...cur, j]));

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-3xl font-semibold tracking-tight text-balance">
        Does your privacy policy match what your code does?
      </h1>
      <p className="mt-3 text-muted-foreground">
        Groundtruth scans your repository and live site, compares the evidence with your policy, and maps each
        possible inconsistency to official law in the UK, EU and Kazakhstan.
      </p>

      <form onSubmit={submit} className="mt-10 space-y-5">
        {FIELDS.map((f) => (
          <div key={f.name} className="space-y-2">
            <Label htmlFor={f.name}>{f.label}</Label>
            <Input
              id={f.name}
              type="url"
              required
              placeholder={f.placeholder}
              value={form[f.name]}
              onChange={(e) => setForm({ ...form, [f.name]: e.target.value })}
              className="font-mono text-sm"
            />
          </div>
        ))}

        <fieldset className="space-y-2">
          <legend className="text-sm font-medium">Jurisdictions</legend>
          <div className="flex gap-2">
            {JURISDICTIONS.map((j) => (
              <button
                key={j.id}
                type="button"
                aria-pressed={jurisdictions.includes(j.id)}
                onClick={() => toggle(j.id)}
                className={cn(
                  "rounded-md border px-3 py-1.5 text-sm transition-colors",
                  jurisdictions.includes(j.id)
                    ? "border-foreground/40 bg-secondary text-foreground"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                {j.label}
              </button>
            ))}
          </div>
        </fieldset>

        {error && (
          <p role="alert" className="rounded-md border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-300">
            {error}
          </p>
        )}

        <div className="flex flex-wrap items-center gap-3 pt-2">
          <Button type="submit" disabled={pending || jurisdictions.length === 0}>
            {pending ? "Starting audit" : "Run audit"}
          </Button>
          <Button type="button" variant="outline" onClick={() => setForm(DEMO)}>
            Use demo fixture
          </Button>
          <Link href="/audit/demo-fixture" className="text-sm text-muted-foreground underline-offset-4 hover:underline">
            View a sample report
          </Link>
        </div>
      </form>

      <p className="mt-10 text-xs text-muted-foreground">
        Public repositories and public pages only. Results are possible inconsistencies for you and your lawyer to
        review, not legal advice.
      </p>
    </div>
  );
}
