# Notely (demo fixture)

A deliberately non-compliant mini product used as the Groundtruth demo target. Nothing here is installed or run as an app; the code is only scanned, and the two HTML pages are served statically.

Planted issues:
- `src/lib/analytics.ts` sends email + name to Mixpanel and PostHog.
- `src/app/api/chat/route.ts` sends user chat text to OpenAI and logs the user's email.
- `src/lib/billing.ts` sends email to Stripe.
- `public/index.html` loads Google Analytics and PostHog before any consent.
- `privacy.html` claims "we never share your data with third parties", does not mention AI, transfers, retention or deletion.
- There is no delete-account route.

Serve it: `make fixture` (from repo root) → site `http://localhost:4100/public/index.html`, policy `http://localhost:4100/privacy.html`.
