import { type Page, expect, test } from "@playwright/test";

/** Phone and tablet widths (SC-8.24): content first, navigation behind a menu, nothing scrolls sideways. SYNTHETIC data. */

async function demoProspect(page: Page): Promise<string> {
  await page.goto("/prospects");
  await expect(page.getByRole("heading", { name: "Cost reviews" })).toBeVisible();
  const row = page.getByRole("row", { name: /P-1042/ });
  await page.waitForLoadState("networkidle");
  if (!(await row.count())) {
    await page.getByRole("button", { name: "Load synthetic demo" }).first().click();
    await expect(page).toHaveURL(/\/p\/\d+/);
    await page.goto("/prospects");
  }
  await row.click();
  await expect(page).toHaveURL(/\/p\/\d+/);
  return page.url().match(/\/p\/(\d+)/)?.[1] as string;
}

const noSideScroll = async (page: Page) =>
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(
    page.viewportSize()?.width ?? 0,
  );

test.describe("phone", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("content first, menu opens and navigates, steps scroll, no sideways page", async ({ page }) => {
    const pid = await demoProspect(page);
    await page.goto(`/p/${pid}/costs`);
    await expect(page.getByRole("heading", { level: 1 })).toBeInViewport();
    await expect(page.getByRole("navigation", { name: "Main" })).not.toBeInViewport();
    await expect(
      page.getByRole("navigation", { name: "Review workflow" }).getByRole("link", { name: /Costs/ }),
    ).toBeInViewport();
    for (const r of ["documents", "review", "costs", "report"]) {
      await page.goto(`/p/${pid}/${r}`);
      await noSideScroll(page);
    }
    await page.getByRole("button", { name: "Menu", exact: true }).click();
    await expect(page.getByRole("navigation", { name: "Main" })).toBeInViewport();
    await page.keyboard.press("Escape");
    await expect(page.getByRole("navigation", { name: "Main" })).not.toBeInViewport();
    await page.getByRole("button", { name: "Menu", exact: true }).click();
    await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Cost reviews" }).click();
    await expect(page.getByRole("heading", { name: "Cost reviews" })).toBeVisible();
    await expect(page.getByRole("navigation", { name: "Main" })).not.toBeInViewport();
    await noSideScroll(page);
  });
});

test("skip link is the first tab stop and moves focus to the content", async ({ page }) => {
  await page.goto("/prospects");
  await expect(page.getByRole("heading", { name: "Cost reviews" })).toBeVisible();
  await page.keyboard.press("Tab");
  const skip = page.getByRole("link", { name: "Skip to content" });
  await expect(skip).toBeFocused();
  await skip.press("Enter");
  await expect(page.locator("main#main")).toBeFocused();
});
