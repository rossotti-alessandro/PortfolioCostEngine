import { expect, test } from "@playwright/test";

/** Team & access (SC-11.12): an admin adds a read-only person who chooses a password and cannot write. SYNTHETIC. */

test("admin adds a viewer; the viewer sets a password, reads, cannot write, and sign-out ends the session", async ({
  page,
  browser,
}) => {
  const username = `e2e.viewer${Date.now() % 100000}`;
  await page.goto("/crm");
  await page.goto("/admin");
  await expect(page.getByRole("heading", { name: "Team & access" })).toBeVisible();
  await page.getByRole("button", { name: "Add a person" }).click();
  const add = page.getByRole("dialog");
  await add.getByLabel("Username").fill(username);
  await add.getByLabel("Full name").fill("SYNTHETIC Viewer");
  await add.getByLabel(/^Analyst/).uncheck();
  await add.getByLabel(/^Viewer \(read-only\)/).check();
  await add.getByRole("button", { name: "Add and show password" }).click();
  const otp = (await page.getByTestId("one-time-password").textContent())?.trim() as string;
  expect(otp.length).toBeGreaterThanOrEqual(12);
  await page.getByRole("button", { name: "Done" }).click();
  await expect(page.getByRole("list", { name: "People" }).getByText(username)).toBeVisible();
  await page.evaluate(() => localStorage.removeItem("pce.role"));

  const ctx = await browser.newContext({ storageState: { cookies: [], origins: [] } });
  const p = await ctx.newPage();
  await p.goto("/crm");
  await p.getByLabel("Username").fill(username);
  await p.getByLabel("Password").fill(otp);
  await p.getByRole("button", { name: "Sign in" }).click();
  await expect(p.getByRole("heading", { name: "Choose your password" })).toBeVisible();
  const pw = "SYNTHETIC viewer passphrase 1";
  await p.getByLabel("One-time password").fill(otp);
  await p.getByLabel("New password (12+ characters)").fill(pw);
  await p.getByLabel("New password again").fill(pw);
  await p.getByRole("button", { name: "Save password" }).click();
  await expect(p.getByRole("heading", { name: "Clients & pipeline" })).toBeVisible();
  await expect(p.getByRole("link", { name: "Team & access" })).toHaveCount(0);

  const csrf = await p.evaluate(async () => (await (await fetch("/api/auth/me")).json()).csrf_token);
  const write = await p.request.post("/api/crm/contacts", {
    data: { name: "SYNTHETIC should fail" },
    headers: { "X-CSRF-Token": csrf },
  });
  expect(write.status()).toBe(403);

  const cookies = await ctx.cookies();
  await p.getByLabel("Account menu").click();
  await p.getByRole("button", { name: "Sign out" }).click();
  await expect(p.getByRole("heading", { name: "Sign in" })).toBeVisible();
  // The copied cookie is dead on the server too.
  const thief = await browser.newContext({ storageState: { cookies, origins: [] } });
  expect((await thief.request.get("http://127.0.0.1:5173/api/prospects")).status()).toBe(401);
  await thief.close();
  await ctx.close();
});
