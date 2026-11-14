import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { SiteHeader } from "@/components/SiteHeader";
import { StartTourButton } from "@/components/tour/TourDock";
import { TOUR_STEPS } from "@/lib/tour";

export const metadata: Metadata = {
  title: "Guided tour | ProveryAI",
  description: "A nine-step walk through ProveryAI for judges: every feature, with the recorded demo audit.",
};

const OUTSIDE = [
  {
    title: "Release gate",
    text: "The same audit runs from a terminal and fails the build when a result is bad enough.",
    code: "make audit repo=demo/fixture-app policy=demo/fixture-app/privacy.html",
  },
  {
    title: "GitHub Action",
    text: "action.yml in the repository runs the same audit on pull requests.",
  },
  {
    title: "AI assistants",
    text: "mcp/server.py exposes the audit as one tool, audit_product, for Claude Code, Cursor and Claude Desktop.",
  },
];

export default function TourPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <SiteHeader />
      <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-12 sm:px-6">
        <p className="text-sm text-muted-foreground">For judges</p>
        <h1 className="mt-2 text-[clamp(2rem,4.5vw,3.25rem)] leading-[1.05] font-semibold tracking-tight text-balance text-foreground">
          See every feature in about five minutes
        </h1>
        <p className="mt-4 max-w-2xl text-base leading-relaxed text-foreground/80">
          The tour walks through a recorded audit of a demo product, so it works even when the audit service is not
          running. A small panel in the corner tells you what to click at each step and what it shows.
        </p>
        <div className="mt-6 flex flex-wrap items-center gap-4">
          <StartTourButton />
          <span className="text-sm text-muted-foreground">or read the steps below and open the pages yourself</span>
        </div>

        <ol className="mt-12 space-y-10">
          {TOUR_STEPS.map((step, index) => (
            <li key={step.id} className="grid grid-cols-[2.5rem_minmax(0,1fr)] gap-x-4">
              <p aria-hidden className="font-serif text-4xl leading-none text-paper/90 tabular-nums">
                {index + 1}
              </p>
              <div className="space-y-2">
                <h2 className="text-xl font-semibold tracking-tight text-foreground">{step.title}</h2>
                <p className="text-foreground/90">{step.action}</p>
                <ul className="space-y-1.5 text-sm leading-relaxed text-muted-foreground">
                  {step.look.map((line) => (
                    <li key={line}>{line}</li>
                  ))}
                </ul>
                <Link
                  href={step.href}
                  className="group inline-flex items-center gap-1 rounded-md text-sm text-signal outline-none hover:underline focus-visible:ring-3 focus-visible:ring-ring/50"
                >
                  Open this page
                  <ArrowRight aria-hidden className="size-3.5 transition-transform group-hover:translate-x-0.5" />
                </Link>
              </div>
            </li>
          ))}
        </ol>

        <section aria-labelledby="outside" className="mt-14 border-t border-white/[0.07] pt-8">
          <h2 id="outside" className="text-sm font-medium text-muted-foreground">
            Outside this page
          </h2>
          <ul className="mt-5 grid gap-6 sm:grid-cols-3">
            {OUTSIDE.map((item) => (
              <li key={item.title} className="space-y-1.5">
                <p className="font-medium text-foreground">{item.title}</p>
                <p className="text-sm leading-relaxed text-muted-foreground">{item.text}</p>
                {item.code && <code className="block font-mono text-xs break-all text-foreground/80">{item.code}</code>}
              </li>
            ))}
          </ul>
        </section>

        <p className="mt-12 text-xs text-muted-foreground">
          A first-pass engineering check, not legal advice. Results are worded as possible inconsistencies for a lawyer
          to review.
        </p>
      </main>
    </div>
  );
}
