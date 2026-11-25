import { expect, test } from "@playwright/test";

/** Activity log (SC-11.8): the admin sees sign-ins with a passed tamper check, also on a phone. SYNTHETIC. */
test("activity log lists sign-ins and shows the tamper check", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/activity");
  await expect(page.getByRole("heading", { name: "Activity log" })).toBeVisible();
  await expect(page.getByText(/Tamper check passed: \d+ entries/)).toBeVisible();
  await page.getByLabel("Show").selectOption({ label: "Sign-ins" });
  await expect(page.getByRole("list", { name: "Activity" }).getByText("Signed in").first()).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});
