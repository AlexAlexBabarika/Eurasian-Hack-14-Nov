"use client";

import { useEffect, useState } from "react";

const GLYPHS = "abcdefghijklmnopqrstuvwxyz0123456789#$%&/<>{}[]=+*";

// Letters resolve left to right out of random characters, once on mount. Decorative: the parent
// must carry the readable text (for example in aria-label), this renders aria-hidden.
export function ScrambleText({
  text,
  startAfter = 0,
  duration = 1100,
  className,
}: {
  text: string;
  startAfter?: number;
  duration?: number;
  className?: string;
}) {
  const [shown, setShown] = useState(text);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    let frame = 0;
    const start = performance.now() + startAfter;
    const tick = (now: number) => {
      const t = Math.max(0, Math.min(1, (now - start) / duration));
      const resolved = Math.floor(t * text.length);
      setShown(
        text
          .split("")
          .map((char, i) => (i < resolved || char === " " ? char : GLYPHS[Math.floor(Math.random() * GLYPHS.length)]))
          .join(""),
      );
      if (t < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [text, startAfter, duration]);

  // The final text reserves the space, so the changing letters never move the layout.
  return (
    <span aria-hidden className={className} style={{ position: "relative", display: "block" }}>
      <span className="invisible">{text}</span>
      <span className="absolute inset-0">{shown}</span>
    </span>
  );
}
