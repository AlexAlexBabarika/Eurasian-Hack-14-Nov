"use client";

import { useLayoutEffect, useRef, useState } from "react";
import { CircleAlert } from "lucide-react";

// Real lines from the demo project's policy and code (api/data/audits/demo-fixture.json).
const EVIDENCE = [
  { where: "src/lib/analytics.ts:1", what: 'import mixpanel from "mixpanel-browser"' },
  { where: "src/app/api/chat/route.ts:12", what: "openai.chat.completions.create({" },
  { where: "network, before consent", what: "GET eu.i.posthog.com/e/" },
  { where: "network, before consent", what: "GET www.google-analytics.com/g/collect" },
];

const delay = (ms: number) => ({ "--delay": `${ms}ms` }) as React.CSSProperties;

// The whole product in one picture: the policy as a sheet of paper, the product as machine output,
// and a line drawn from the sentence to the code that contradicts it. Plays once on load.
export function HeroExhibit() {
  const stage = useRef<HTMLElement>(null);
  const from = useRef<HTMLSpanElement>(null);
  const to = useRef<HTMLLIElement>(null);
  const [line, setLine] = useState<{ d: string; x: number; y: number } | null>(null);

  useLayoutEffect(() => {
    const measure = () => {
      if (!stage.current || !from.current || !to.current) return;
      const box = stage.current.getBoundingClientRect();
      const fragments = from.current.getClientRects();
      const last = fragments[fragments.length - 1];
      const target = to.current.getBoundingClientRect();
      if (!last) return;
      const x1 = last.right - box.left;
      const y1 = last.top - box.top + last.height * 0.6;
      const x2 = target.left - box.left - 10;
      const y2 = target.top - box.top + target.height / 2;
      // Side by side only; when the cards stack there is nothing to connect across.
      if (x2 - x1 < 24) return setLine(null);
      const bend = Math.max(32, (x2 - x1) / 2);
      setLine({ d: `M ${x1} ${y1} C ${x1 + bend} ${y1}, ${x2 - bend} ${y2}, ${x2} ${y2}`, x: x2, y: y2 });
    };
    measure();
    const observer = new ResizeObserver(measure);
    if (stage.current) observer.observe(stage.current);
    document.fonts?.ready.then(measure).catch(() => {});
    return () => observer.disconnect();
  }, []);

  return (
    <figure
      ref={stage}
      aria-label="Example from the demo project: the policy says data is never shared, while the code sends it to Mixpanel, OpenAI, PostHog and Google Analytics."
      className="relative grid gap-4 sm:grid-cols-[minmax(0,5fr)_minmax(0,6fr)] sm:gap-12"
    >
      <div aria-hidden className="paper self-start rounded-xl p-5 font-serif shadow-2xl shadow-black/50">
        <p className="mb-3 font-sans text-[11px] font-medium text-paper-ink/55">privacy.html</p>
        <p className="text-[19px] leading-7">Privacy Policy</p>
        <p className="mt-2 text-[15px] leading-7 text-paper-ink/85">
          We collect your email address and password when you create an account.{" "}
          <span ref={from} className="marker animate-marker text-paper-ink" style={delay(700)}>
            We never share your data with third parties.
          </span>
        </p>
      </div>

      <div
        aria-hidden
        className="overflow-hidden rounded-xl border border-white/10 bg-ink p-5 font-mono text-[12.5px] leading-6 shadow-2xl shadow-black/50 sm:mt-10"
      >
        <p className="mb-3 flex items-center gap-2 font-sans text-[11px] font-medium text-muted-foreground">
          <span className="tone-signal animate-pulse-dot size-1.5 rounded-full bg-signal" />
          what the product does
        </p>
        <ul className="space-y-2">
          {EVIDENCE.map((item, i) => (
            <li key={item.what} ref={i === 0 ? to : undefined} className="animate-type" style={delay(2500 + i * 480)}>
              <span className="block truncate text-[11px] leading-4 text-muted-foreground">{item.where}</span>
              <span className="block truncate text-foreground">
                <span className="mr-2 text-status-red">+</span>
                {item.what}
              </span>
            </li>
          ))}
        </ul>
        <p
          className="tone-red tone-edge animate-fade mt-4 inline-flex items-center gap-1.5 rounded-md bg-status-red/12 px-2 py-1 font-sans text-xs font-medium text-status-red"
          style={delay(4500)}
        >
          <CircleAlert className="size-3.5" />
          Possible inconsistency with GDPR Art. 13(1)(e)
        </p>
      </div>

      {line && (
        <svg aria-hidden className="pointer-events-none absolute inset-0 size-full overflow-visible">
          <path
            d={line.d}
            pathLength={1}
            fill="none"
            stroke="var(--status-red)"
            strokeWidth={2}
            strokeLinecap="round"
            className="animate-draw"
            style={delay(1600)}
          />
          <circle cx={line.x} cy={line.y} r={4} fill="var(--status-red)" className="animate-fade" style={delay(2500)} />
        </svg>
      )}
    </figure>
  );
}
