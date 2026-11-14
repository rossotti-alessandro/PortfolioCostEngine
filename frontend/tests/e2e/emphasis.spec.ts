import { type Page, expect, test } from "@playwright/test";

/** Answer first, fewer choices (SC-8.27) on the SYNTHETIC demo prospect. */

async function demoProspect(page: Page): Promise<string> {
  await page.goto("/prospects");
  await expect(page.getByRole("heading", { name: "Cost reviews" })).toBeVisible();
  await page.waitForLoadState("networkidle");
  const row = page.getByRole("row", { name: /P-1042/ });
  if (!(await row.count())) {
    await page.getByRole("button", { name: "Load synthetic demo" }).first().click();
    await expect(page).toHaveURL(/\/p\/\d+/);
    await page.goto("/prospects");
  }
  await row.click();
  return page.url().match(/\/p\/(\d+)/)?.[1] as string;
}

test("Compare leads with the annual saving and folds the proposal lines", async ({ page }) => {
  const pid = await demoProspect(page);
  await page.goto(`/p/${pid}/compare`);
  const saving = page.getByText("Annual saving", { exact: true }).first();
  const today = page.getByText("Today (comparable)", { exact: true }).first();
  await expect(saving).toBeVisible();
  const [s, t] = [await saving.boundingBox(), await today.boundingBox()];
  expect((s?.x ?? 0) + (s?.y ?? 0) * 10).toBeLessThan((t?.x ?? 0) + (t?.y ?? 0) * 10);

  const more = page.getByRole("button", { name: /^Show all \d+ lines$/ });
  await expect(more).toHaveAttribute("aria-expanded", "false");
  await more.click();
  await expect(page.getByRole("button", { name: "Show fewer" })).toBeVisible();
});

test("Costs shows the two biggest requests first", async ({ page }) => {
  const pid = await demoProspect(page);
  await page.goto(`/p/${pid}/costs`);
  const marks = page.getByRole("button", { name: "Mark requested" });
  await expect(marks).toHaveCount(2);
  await page.getByRole("button", { name: /^Show all \d+ requests$/ }).click();
  expect(await marks.count()).toBeGreaterThan(2);
});
