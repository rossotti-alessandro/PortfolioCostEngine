import { type Page, expect, test } from "@playwright/test";

/** Phone scan (SC-8.28): photos of paper pages become one PDF document. Images are drawn in the page: SYNTHETIC. */

test.use({ viewport: { width: 390, height: 844 } });

async function newProspect(page: Page): Promise<string> {
  const csrf = await page.evaluate(async () => (await (await fetch("/api/auth/me")).json()).csrf_token);
  const r = await page.request.post("/api/prospects", {
    data: { code: `SCAN-${Date.now()}`, label: "SYNTHETIC scan", domicile: "CH" },
    headers: { "X-CSRF-Token": csrf },
  });
  return String((await r.json()).id);
}

/** A JPEG "photo" of a printed page, drawn on a canvas in the browser. */
async function pagePhoto(page: Page, text: string): Promise<Buffer> {
  const b64 = await page.evaluate((txt) => {
    const c = document.createElement("canvas");
    c.width = 1240;
    c.height = 1754;
    const g = c.getContext("2d") as CanvasRenderingContext2D;
    g.fillStyle = "white";
    g.fillRect(0, 0, c.width, c.height);
    g.fillStyle = "black";
    g.font = "56px sans-serif";
    g.fillText("SYNTHETIC DEMO STATEMENT", 80, 160);
    g.fillText(txt, 80, 280);
    return c.toDataURL("image/jpeg", 0.9).split(",")[1];
  }, text);
  return Buffer.from(b64, "base64");
}

test("scan two pages with the camera and save them as one document", async ({ page }) => {
  await page.goto("/crm");
  const pid = await newProspect(page);
  await page.goto(`/p/${pid}/documents`);
  await page.getByRole("button", { name: "Scan with camera" }).click();
  const dialog = page.getByRole("dialog");
  const shot = dialog.getByLabel("Take a photo of a page");
  await expect(shot).toHaveAttribute("capture", "environment");
  await shot.setInputFiles({ name: "IMG_0001.jpg", mimeType: "image/jpeg", buffer: await pagePhoto(page, "Page one") });
  await expect(dialog.getByRole("img", { name: "Page 1" })).toBeVisible();
  await shot.setInputFiles({ name: "IMG_0002.jpg", mimeType: "image/jpeg", buffer: await pagePhoto(page, "Page two") });
  await expect(dialog.getByRole("img", { name: "Page 2" })).toBeVisible();
  await dialog.getByRole("button", { name: "Move page 2 earlier" }).click();
  await dialog.getByLabel("Document name (optional)").fill("Paper statement SYNTHETIC");
  await dialog.getByRole("button", { name: "Save as one document (2 pages)" }).click();
  await expect(dialog).toHaveCount(0, { timeout: 90_000 });
  await expect(page.getByText("Paper statement SYNTHETIC.pdf").first()).toBeVisible({ timeout: 90_000 });
  const docs = await (await page.request.get(`/api/prospects/${pid}/documents`)).json();
  expect(docs).toHaveLength(1);
  expect(docs[0].pages).toHaveLength(2);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
});
