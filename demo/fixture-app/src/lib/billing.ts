import Stripe from "stripe";

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY ?? "");

export async function createCustomer(user: { email: string; name: string }) {
  return stripe.customers.create({ email: user.email, name: user.name });
}
