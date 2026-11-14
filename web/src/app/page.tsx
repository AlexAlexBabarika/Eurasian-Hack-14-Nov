import Link from "next/link";
import { ArrowRight, Braces, Scale, ScanSearch } from "lucide-react";

import { AuditForm } from "@/components/AuditForm";
import { SiteHeader } from "@/components/SiteHeader";
import { StatusIcon } from "@/components/StatusBadge";
import { DEMO_ID } from "@/lib/api";

const HOW = [
  {
    icon: Braces,
    title: "Reads what the product does",
    text: "Dependencies, source code and the requests your site makes before anyone clicks Accept.",
  },
  {
    icon: ScanSearch,
    title: "Compares it with your policy",
    text: "Each mismatch is shown next to the exact sentence of the policy and the exact line of code.",
  },
  {
    icon: Scale,
    title: "Maps it to the law",
    text: "Every result cites a specific provision in UK, EU or Kazakhstan law, with a link to the official text.",
  },
];

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col">
      <SiteHeader>
        <Link
          href={`/audit/${DEMO_ID}`}
          className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-sm text-muted-foreground outline-none hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50"
        >
          See an example report
          <ArrowRight aria-hidden className="size-3.5" />
        </Link>
      </SiteHeader>

      <main className="mx-auto grid w-full max-w-6xl flex-1 content-start gap-x-16 gap-y-8 px-4 py-10 sm:px-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,520px)] lg:py-16">
        <section className="space-y-4 lg:pt-4">
          <p className="text-xs font-medium tracking-widest text-muted-foreground uppercase">Privacy policy vs. code</p>
          <h1 className="text-3xl leading-tight font-semibold tracking-tight text-balance text-foreground sm:text-4xl">
            Does your privacy policy match what your product actually does?
          </h1>
          <p className="max-w-xl text-base leading-relaxed text-muted-foreground">
            Paste three links. Groundtruth compares the code and the live site with the policy and shows every possible
            inconsistency with evidence, the provision it relates to, and text you can paste to fix it.
          </p>
        </section>

        <section aria-label="Start an audit" className="lg:col-start-2 lg:row-span-2 lg:row-start-1">
          <AuditForm />
        </section>

        <section aria-label="How it works" className="space-y-8 lg:col-start-1">
          <ol className="space-y-5">
            {HOW.map((item, i) => (
              <li key={item.title} className="flex gap-3.5">
                <span className="flex size-9 shrink-0 items-center justify-center rounded-lg border bg-card text-muted-foreground">
                  <item.icon aria-hidden className="size-4" />
                </span>
                <div className="space-y-0.5">
                  <p className="text-sm font-medium text-foreground">
                    <span className="mr-1.5 text-muted-foreground">{i + 1}.</span>
                    {item.title}
                  </p>
                  <p className="text-sm text-muted-foreground">{item.text}</p>
                </div>
              </li>
            ))}
          </ol>

          <div className="rounded-xl border border-dashed p-4">
            <p className="mb-2.5 text-xs text-muted-foreground">You get one verdict per country and area of law:</p>
            <ul className="grid gap-x-6 gap-y-1.5 text-sm text-foreground/90 sm:grid-cols-2">
              <li className="flex items-center gap-2">
                <StatusIcon status="red" /> Possible inconsistency
              </li>
              <li className="flex items-center gap-2">
                <StatusIcon status="amber" /> Needs review
              </li>
              <li className="flex items-center gap-2">
                <StatusIcon status="green" /> No issues found
              </li>
              <li className="flex items-center gap-2">
                <StatusIcon status="grey" /> Not assessed
              </li>
            </ul>
          </div>
        </section>
      </main>

      <footer className="border-t">
        <p className="mx-auto w-full max-w-6xl px-4 py-4 text-xs text-muted-foreground sm:px-6">
          A first-pass engineering check, not legal advice. Results are worded as possible inconsistencies for a lawyer to
          review.
        </p>
      </footer>
    </div>
  );
}
