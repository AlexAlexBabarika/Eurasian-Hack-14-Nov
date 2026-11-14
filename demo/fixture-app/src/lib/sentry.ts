import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: "https://examplePublicKey@o0.ingest.sentry.io/0",
  sendDefaultPii: true,
  tracesSampleRate: 1.0,
});

export function setSentryUser(user: { id: string; email: string }) {
  Sentry.setUser({ id: user.id, email: user.email });
}
