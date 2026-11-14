import Link from "next/link";

export function Wordmark() {
  return (
    <Link
      href="/"
      translate="no"
      className="group flex items-center gap-2.5 rounded-md text-[15px] font-semibold tracking-tight text-foreground outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
    >
      {/* Two lines of a document; the second one is struck through. */}
      <span
        aria-hidden
        className="flex size-7 items-center justify-center rounded-md bg-paper text-paper-ink transition-transform duration-200 group-hover:-rotate-6"
      >
        <svg viewBox="0 0 16 16" className="size-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
          <path d="M3 5h10M3 11h6" />
          <path d="M11.5 9.5l3 3M14.5 9.5l-3 3" className="text-status-red" stroke="currentColor" />
        </svg>
      </span>
      ProveryAI
    </Link>
  );
}

export function SiteHeader({ children }: { children?: React.ReactNode }) {
  return (
    <header className="sticky top-0 z-30 border-b border-white/[0.07] bg-background/70 backdrop-blur-xl">
      <div className="mx-auto flex h-14 w-full max-w-7xl items-center justify-between gap-4 px-4 sm:px-6">
        <Wordmark />
        <div className="flex min-w-0 items-center gap-2">{children}</div>
      </div>
    </header>
  );
}
