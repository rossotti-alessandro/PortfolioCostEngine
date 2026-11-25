import { expect, test } from "@playwright/test";

/** Erasure on request (SC-11.11): a senior erases a cost review; the activity log still passes its check. SYNTHETIC. */
test("a senior erases a cost review and the tamper check still passes", async ({ page }) => {
  const code = `ERASE-${Date.now() % 100000}`;
  await page.goto("/crm");
  await page.evaluate(() => localStorage.setItem("pce.role", "senior"));
  const csrf = await page.evaluate(async () => (await (await fetch("/api/auth/me")).json()).csrf_token);
  const made = await page.request.post("/api/prospects", {
    data: { code, label: "SYNTHETIC erase", domicile: "CH" },
    headers: { "X-CSRF-Token": csrf, "X-Role": "senior" },
  });
  expect(made.status()).toBe(201);

  await page.goto("/prospects");
  await page.getByRole("button", { name: `Erase ${code}` }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel(`Type ${code} to confirm`).fill(code);
  await dialog.getByRole("button", { name: "Erase" }).click();
  await expect(page.getByRole("button", { name: `Erase ${code}` })).toHaveCount(0);

  await page.goto("/activity");
  await expect(page.getByText(/Tamper check passed/)).toBeVisible();
  await expect(page.getByText("Erased a cost review").first()).toBeVisible();
  await page.evaluate(() => localStorage.removeItem("pce.role"));
});
