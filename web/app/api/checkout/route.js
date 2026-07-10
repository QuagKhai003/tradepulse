/**
 * route.js — POST /api/checkout: TEST-MODE tier switch (plan §11).
 * @context  Stands in for a real payment provider. `action=upgrade` sets the paid cookie,
 *           `action=cancel` reverts to free. A production provider's webhook replaces this,
 *           flipping the same cookie/session — pages don't change.
 * @limits   No real charge. Cookie only. Never trust the client for money in production.
 * @affects  Sets tp_tier; pages read it via lib/tier.getTier.
 */
import { NextResponse } from "next/server";

export async function POST(request) {
  const form = await request.formData().catch(() => null);
  const action = form?.get("action") === "cancel" ? "cancel" : "upgrade";
  const dest = action === "cancel" ? "/pricing?downgraded=1" : "/pricing?upgraded=1";
  const res = NextResponse.redirect(new URL(dest, request.url), 303);
  res.cookies.set("tp_tier", action === "cancel" ? "free" : "paid", {
    path: "/", maxAge: 60 * 60 * 24 * 30, sameSite: "lax",
  });
  return res;
}
