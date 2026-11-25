import { createHmac } from "node:crypto";
import { expect, test } from "@playwright/test";

/** RFC 6238 TOTP (SHA-1, 30 s, 6 digits), like an authenticator app. */
function totp(secret: string, offset = 0): string {
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
  let bits = "";
  for (const ch of secret.replace(/\s/g, "")) bits += alphabet.indexOf(ch).toString(2).padStart(5, "0");
  const key = Buffer.from(bits.match(/.{8}/g)?.map((b) => Number.parseInt(b, 2)) ?? []);
  const step = Buffer.alloc(8);
  step.writeBigUInt64BE(BigInt(Math.floor(Date.now() / 30000) + offset));
  const mac = createHmac("sha1", key).update(step).digest();
  const off = mac[mac.length - 1] & 0x0f;
  return String((mac.readUInt32BE(off) & 0x7fffffff) % 1_000_000).padStart(6, "0");
}

/** Two-step sign-in (SC-11.7) on a phone: turn it on from the account menu, then sign in with a code. SYNTHETIC. */
test("a person turns on two-step sign-in and then needs the code", async ({ page, browser }) => {
  const username = `e2e.mfa${Date.now() % 100000}`;
  await page.goto("/crm");
  const csrf = await page.evaluate(async () => (await (await fetch("/api/auth/me")).json()).csrf_token);
  const made = await page.request.post("/api/admin/users", {
    data: { username, roles: ["analyst"] },
    headers: { "X-CSRF-Token": csrf, "X-Role": "admin" },
  });
  const otp = (await made.json()).one_time_password as string;

  const ctx = await browser.newContext({
    storageState: { cookies: [], origins: [] },
    viewport: { width: 390, height: 844 },
  });
  const p = await ctx.newPage();
  await p.goto("/crm");
  await p.getByLabel("Username").fill(username);
  await p.getByLabel("Password").fill(otp);
  await p.getByRole("button", { name: "Sign in" }).click();
  const pw = "SYNTHETIC mfa passphrase 1";
  await p.getByLabel("One-time password").fill(otp);
  await p.getByLabel("New password (12+ characters)").fill(pw);
  await p.getByLabel("New password again").fill(pw);
  await p.getByRole("button", { name: "Save password" }).click();
  await expect(p.getByRole("heading", { name: "Clients & pipeline" })).toBeVisible();

  await p.goto("/account/two-step");
  await expect(p.getByRole("heading", { name: "Two-step sign-in" })).toBeVisible();
  const secret = ((await p.locator("code").first().textContent()) ?? "").replace(/\s/g, "");
  await p.getByLabel("Code from your authenticator app").fill(totp(secret));
  await p.getByRole("button", { name: "Turn on two-step sign-in" }).click();
  await expect(p.getByRole("heading", { name: "Clients & pipeline" })).toBeVisible();

  await p.getByRole("button", { name: "Open menu" }).click();
  await p.getByLabel("Account menu").click();
  await p.getByRole("button", { name: "Sign out" }).click();
  await p.getByLabel("Username").fill(username);
  await p.getByLabel("Password").fill(pw);
  await p.getByRole("button", { name: "Sign in" }).click();
  await p.getByLabel("Code from your authenticator app").fill(totp(secret, 1));
  await p.getByRole("button", { name: "Sign in" }).click();
  await expect(p.getByRole("heading", { name: "Clients & pipeline" })).toBeVisible();
  await ctx.close();
});
