/**
 * tier.js — read the current subscription tier (plan §11 monetization).
 * @context  MVP tier lives in a cookie set by the test-mode checkout. Server-only. Real billing
 *           (a provider webhook flipping the tier) swaps in behind getTier() with no caller change.
 * @limits   Read-only here; the cookie is written by /api/checkout.
 * @affects  Used by profiles + requirements pages to gate paid content.
 */
import { cookies } from "next/headers";

export const PRICE_VND = 200000; // monthly (plan §11 hypothesis: 200k–500k VND)

export async function getTier() {
  const c = await cookies();
  return c.get("tp_tier")?.value === "paid" ? "paid" : "free";
}
