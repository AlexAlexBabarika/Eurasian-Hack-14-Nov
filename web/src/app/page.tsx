import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { AuditForm } from "@/components/AuditForm";
import { HeroExhibit } from "@/components/HeroExhibit";
import { ScrambleText } from "@/components/ScrambleText";
import LetterGlitch from "@/components/reactbits/LetterGlitch";
import { SiteHeader } from "@/components/SiteHeader";
import { StatusIcon } from "@/components/StatusBadge";
import { DEMO_ID } from "@/lib/api";
import { STATUS_LABEL } from "@/lib/labels";
import type { Status } from "@/lib/types";

const HOW = [
  {
    title: "Reads what the product does",
    text: "Dependencies, source code and the requests your site makes before anyone clicks Accept.",
  },
  {
    title: "Compares it with your policy",
    text: "Each mismatch sits next to the exact sentence of the policy and the exact line of code.",
  },
  {
    title: "Maps it to the law",
    text: "Every result cites a specific provision in UK, EU or Kazakhstan law, with a link to the official text.",
  },
];

const LEGEND: Status[] = ["red", "amber", "green", "grey"];

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col overflow-x-clip">
      <SiteHeader>
        <Link
          href={`/audit/${DEMO_ID}`}
          className="group inline-flex items-center gap-1 rounded-md px-2 py-1 text-sm text-muted-foreground outline-none transition-colors hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50"
        >
          See an example report
          <ArrowRight aria-hidden className="size-3.5 transition-transform group-hover:translate-x-0.5" />
        </Link>
      </SiteHeader>

      <main className="flex-1">
        <div className="relative isolate border-b border-white/[0.07]">
          {/* Field of code characters behind the first screen. */}
          <div aria-hidden className="pointer-events-none absolute inset-0 -z-10">
            <LetterGlitch
              glitchColors={["#5db8ff", "#ff5a52", "#f4efe2"]}
              baseOpacity={0.12}
              glitchAmount={0.35}
              speed={0.6}
              interactive={false}
              clickEffect="none"
              className="size-full"
            />
          </div>
        <div className="mx-auto grid w-full max-w-7xl grid-cols-[minmax(0,1fr)] content-start px-4 sm:px-6 gap-x-14 gap-y-8 py-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,480px)] lg:py-12">
          <section className="space-y-4">
            <h1
              aria-label="Your privacy policy makes promises. Your code keeps the receipts."
              className="animate-rise text-[clamp(2.5rem,5.4vw,4.25rem)] leading-[1] tracking-tight text-balance"
            >
              <span aria-hidden className="block font-serif text-paper">
                Your privacy policy makes promises.
              </span>
              <ScrambleText
                text="Your code keeps the receipts."
                startAfter={250}
                className="font-semibold tracking-tighter text-foreground"
              />
            </h1>
            <p
              className="animate-rise max-w-xl text-base leading-relaxed text-foreground/80 sm:text-lg"
              style={{ "--i": 2 } as React.CSSProperties}
            >
              Paste three links. Groundtruth compares the code and the live site with the policy and shows every possible
              inconsistency with evidence, the provision it relates to, and text you can paste to fix it.
            </p>
          </section>

          <section
            aria-label="Start an audit"
            className="animate-rise lg:sticky lg:top-20 lg:col-start-2 lg:row-span-2 lg:row-start-1 lg:self-start"
            style={{ "--i": 3 } as React.CSSProperties}
          >
            <AuditForm />
          </section>

          <div className="animate-rise lg:col-start-1" style={{ "--i": 4 } as React.CSSProperties}>
            <HeroExhibit />
          </div>
        </div>
        </div>

        <section aria-labelledby="how" className="mx-auto w-full max-w-7xl px-4 py-12 sm:px-6">
          <h2 id="how" className="text-sm font-medium text-muted-foreground">
            How an audit works
          </h2>
          <ol className="mt-6 grid gap-8 md:grid-cols-3">
            {HOW.map((item, i) => (
              <li key={item.title} className="space-y-2">
                <p className="font-serif text-5xl leading-none text-paper/90 tabular-nums">{i + 1}</p>
                <p className="text-lg font-medium tracking-tight text-foreground">{item.title}</p>
                <p className="text-sm leading-relaxed text-muted-foreground">{item.text}</p>
              </li>
            ))}
          </ol>

          <div className="mt-12 space-y-3">
            <p className="text-sm text-muted-foreground">You get one verdict per country and area of law:</p>
            <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {LEGEND.map((status) => (
                <li key={status} className={`tone-${status} tone-wash tone-edge space-y-1 rounded-xl p-4`}>
                  <p className="flex items-center gap-2 text-sm font-medium text-foreground">
                    <StatusIcon status={status} /> {STATUS_LABEL[status].name}
                  </p>
                  <p className="text-xs leading-relaxed text-muted-foreground">{STATUS_LABEL[status].description}</p>
                </li>
              ))}
            </ul>
          </div>
        </section>
      </main>

      <footer className="border-t border-white/[0.07]">
        <p className="mx-auto w-full max-w-7xl px-4 py-4 text-xs text-muted-foreground sm:px-6">
          A first-pass engineering check, not legal advice. Results are worded as possible inconsistencies for a lawyer to
          review.
        </p>
      </footer>
    </div>
  );
}
