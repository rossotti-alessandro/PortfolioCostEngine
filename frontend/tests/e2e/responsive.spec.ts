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
    for (const r of ["documents", "review", "costs", "compare", "report", "internal"]) {
      await page.goto(`/p/${pid}/${r}`);
      await noSideScroll(page);
    }
    await page.getByRole("button", { name: "Open menu", exact: true }).click();
    await expect(page.getByRole("navigation", { name: "Main" })).toBeInViewport();
    await page.keyboard.press("Escape");
    await expect(page.getByRole("navigation", { name: "Main" })).not.toBeInViewport();
    await page.getByRole("button", { name: "Open menu", exact: true }).click();
    await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Cost reviews" }).click();
    await expect(page.getByRole("heading", { name: "Cost reviews" })).toBeVisible();
    await expect(page.getByRole("navigation", { name: "Main" })).not.toBeInViewport();
    await noSideScroll(page);
  });
});

test("wide window collapses the sidebar and keeps it closed", async ({ page }) => {
  await page.addInitScript(() => localStorage.removeItem("feelens.nav"));
  await page.goto("/crm");
  const nav = page.getByRole("navigation", { name: "Main" });
  await expect(nav).toBeVisible();
  const main = page.locator("main#main");
  const openWidth = (await main.boundingBox())?.width ?? 0;
  await page.getByRole("button", { name: "Close menu", exact: true }).click();
  await expect(nav).toBeHidden();
  const closedWidth = (await main.boundingBox())?.width ?? 0;
  expect(closedWidth).toBeGreaterThan(openWidth);
  await page.getByRole("button", { name: "Open menu", exact: true }).click();
  await expect(nav).toBeVisible();
  const restored = (await main.boundingBox())?.width ?? 0;
  expect(restored).toBeLessThan(closedWidth);
  await page.getByRole("button", { name: "Close menu", exact: true }).click();
  // The link is in the collapsed column. A DOM click is a client-side route change, which must not open it again.
  await page.evaluate(() => document.querySelector<HTMLAnchorElement>('#app-nav a[href="/prospects"]')?.click());
  await expect(page.getByRole("heading", { name: "Cost reviews" })).toBeVisible();
  await expect(nav).toBeHidden();
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

test.describe("tablet", () => {
  test.use({ viewport: { width: 820, height: 1180 }, hasTouch: true });

  test("no sideways page, and (i) opens on a tap", async ({ page }) => {
    const pid = await demoProspect(page);
    for (const r of ["documents", "review", "costs", "compare", "report", "internal"]) {
      await page.goto(`/p/${pid}/${r}`);
      await noSideScroll(page);
    }
    await page.goto(`/p/${pid}/documents`);
    await page.getByRole("button", { name: "More information" }).first().tap();
    await expect(page.getByRole("tooltip")).toBeVisible();
  });
});
