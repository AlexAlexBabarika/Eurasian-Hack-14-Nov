import Link from "next/link";

export function Wordmark() {
  return (
    <Link
      href="/"
      className="flex items-center gap-2 rounded-md text-sm font-semibold tracking-tight text-foreground outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
    >
      <span aria-hidden className="flex size-6 items-center justify-center rounded-md bg-foreground text-background">
        <svg viewBox="0 0 16 16" className="size-3.5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
          <path d="M3 5h10M3 11h6" />
          <path d="M11.5 9.5l3 3M14.5 9.5l-3 3" />
        </svg>
      </span>
      Groundtruth
    </Link>
  );
}

export function SiteHeader({ children }: { children?: React.ReactNode }) {
  return (
    <header className="sticky top-0 z-30 border-b bg-background/85 backdrop-blur">
      <div className="mx-auto flex h-14 w-full max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
        <Wordmark />
        <div className="flex items-center gap-2">{children}</div>
      </div>
    </header>
  );
}
