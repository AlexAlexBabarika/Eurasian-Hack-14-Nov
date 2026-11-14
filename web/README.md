# Groundtruth web

Next.js 15 (App Router) + Tailwind v4 + shadcn/ui. Run `pnpm dev` (or `make web` from the repo root); the API must be on `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`).

`src/lib/api-types.ts` is generated from the FastAPI schema: run `make types` from the repo root, never edit by hand.
