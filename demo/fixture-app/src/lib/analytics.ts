import mixpanel from "mixpanel-browser";
import posthog from "posthog-js";

mixpanel.init("demo_mixpanel_token");
posthog.init("phc_demo_key", { api_host: "https://eu.i.posthog.com" });

export type User = { id: string; email: string; name: string };

export function identifyUser(user: User) {
  mixpanel.identify(user.id);
  mixpanel.people.set({
    $email: user.email,
    $name: user.name,
  });
  posthog.identify(user.id, { email: user.email, name: user.name });
}

export function track(event: string, props: Record<string, unknown> = {}) {
  mixpanel.track(event, props);
  posthog.capture(event, props);
}
