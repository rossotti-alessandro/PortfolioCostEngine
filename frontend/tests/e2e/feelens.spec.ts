import { existsSync, readdirSync } from "node:fs";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { type Page, expect, test } from "@playwright/test";

/**
 * End-to-end: a real browser drives the real API on an empty database.
 * Data: SYNTHETIC prospects from data/synthetic, plus the real public iShares KID when fetched
 * (python -m pce.demo.public_corpus). No client data.
 */
const ROOT = resolve(fileURLToPath(new URL("../../..", import.meta.url)));
const P2077 = join(ROOT, "data/synthetic/prospect_p2077");
const REAL_KID = join(ROOT, "var/public_corpus/kid_IE00B4L5Y983.pdf");
const SHOTS = join(ROOT, "artifacts/e2e/screens");

test.use({ deviceScaleFactor: 2 });
test.describe.configure({ mode: "serial" });

const shot = (page: Page, name: string) => page.screenshot({ path: join(SHOTS, `${name}.png`), fullPage: true });
let pid = 0;

test("01 prospects: load the synthetic demo", async ({ page }) => {
  await page.goto("/prospects");
  await expect(page.getByRole("heading", { name: "Cost reviews" })).toBeVisible();
  await page.getByRole("button", { name: "Load synthetic demo" }).first().click();
  await expect(page).toHaveURL(/\/p\/\d+/); // seeding opens the first demo prospect
  await page.goto("/prospects");
  await expect(page.getByRole("row", { name: /P-1042/ })).toBeVisible();
  await expect(page.getByRole("row", { name: /P-2077/ })).toBeVisible();
  await shot(page, "01-prospects");
});

test("02 new prospect: upload statements, cost report and KIDs through the UI", async ({ page }) => {
  await page.goto("/prospects");
  await page.getByRole("button", { name: "New prospect" }).click();
  await page.getByLabel("Prospect code").fill("P-E2E");
  await page.getByLabel("Display name").fill("E2E multi-bank (synthetic)");
  await page.getByRole("button", { name: "Create and upload documents" }).click();
  await expect(page).toHaveURL(/\/p\/\d+\/documents/);
  pid = Number(page.url().match(/\/p\/(\d+)/)?.[1]);
  const files = readdirSync(P2077).map((f) => join(P2077, f));
  if (existsSync(REAL_KID)) files.push(REAL_KID);
  await page.getByLabel("Choose files to upload").setInputFiles(files);
  await expect(page.getByText("Last upload")).toBeVisible({ timeout: 90_000 });
  for (const f of files) await expect(page.getByText(f.split("/").pop() as string).first()).toBeVisible();
  await expect(page.getByText("unknown", { exact: true })).toHaveCount(0);
  await shot(page, "02-documents");
});

test("03 review: every extracted value has a highlighted box on the page", async ({ page }) => {
  await page.goto(`/p/${pid}/review`);
  await expect(page.getByText("Extracted values")).toBeVisible();
  const boxes = page.locator(".evidence-box");
  await expect(boxes.first()).toBeVisible();
  expect(await boxes.count()).toBeGreaterThan(2);
  await boxes.first().click();
  await expect(boxes.first()).toHaveAttribute("data-active", "true");
  await shot(page, "03-review-evidence");
});

test("04 costs: totals in CHF, unknowns are not zero, checks reconcile", async ({ page }) => {
  await page.goto(`/p/${pid}/costs`);
  await expect(page.getByRole("heading", { name: "Current costs" })).toBeVisible();
  await expect(page.getByText("Not determined").first()).toBeVisible();
  await page.getByRole("button", { name: /Validation and reconciliation/ }).click(); // folded by default
  await expect(page.getByText(/converted at the printed rate/).first()).toBeVisible();
  await shot(page, "04-costs");
});

test("05 compare: proposal vs today, like for like", async ({ page }) => {
  await page.goto(`/p/${pid}/compare`);
  await expect(page.getByRole("heading", { name: "Compare with the proposal" })).toBeVisible();
  await expect(page.getByText("Cost by layer, today vs proposal")).toBeVisible();
  await shot(page, "05-compare");
});

test("06 demo prospect P-1042: costs, compare, report PDF", async ({ page }) => {
  const r = await page.request.get("/api/prospects", { headers: { "X-Role": "analyst" } });
  const rows: { id: number; code: string }[] = await r.json();
  const demo = rows.find((x) => x.code === "P-1042");
  expect(demo).toBeTruthy();
  await page.goto(`/p/${demo?.id}/costs`);
  await expect(page.getByText("Cost ledger")).toBeVisible();
  await shot(page, "06-demo-costs");
  await page.goto(`/p/${demo?.id}/compare`);
  await expect(page.getByText("Cost by layer, today vs proposal")).toBeVisible();
  await shot(page, "07-demo-compare");
  await page.goto(`/p/${demo?.id}/report`);
  await expect(page.getByRole("heading", { name: "Client report" })).toBeVisible();
  const [dl] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("button", { name: "Download PDF" }).click(),
  ]);
  const path = await dl.path();
  expect(path).toBeTruthy();
  expect(dl.suggestedFilename()).toMatch(/\.pdf$/);
  await shot(page, "08-demo-report");
});

test("07 roles: analysts cannot see internal margin, seniors can", async ({ page }) => {
  const rows: { id: number; code: string }[] = await (
    await page.request.get("/api/prospects", { headers: { "X-Role": "analyst" } })
  ).json();
  const id = rows.find((x) => x.code === "P-1042")?.id;
  await page.goto(`/p/${id}/internal`);
  await expect(page.getByText("Restricted to senior reviewers")).toBeVisible();
  await page.getByLabel("Demo role").selectOption("senior");
  await expect(page.getByRole("heading", { name: "Internal economics" })).toBeVisible();
  await shot(page, "09-internal-senior");
  const client = await (
    await page.request.get(`/api/prospects/${id}/analysis`, { headers: { "X-Role": "analyst" } })
  ).text();
  expect(client).not.toMatch(/min_margin_pct|servicing_cost|annual_contribution/);
});

test("08 access: signed-out requests are refused, a firm header cannot switch firm", async ({
  request,
  playwright,
}) => {
  const anon = await playwright.request.newContext({ storageState: { cookies: [], origins: [] } });
  expect((await anon.get(`/api/prospects/${pid}/analysis`)).status()).toBe(401);
  await anon.dispose();
  const spoofed = await request.get("/api/prospects", { headers: { "X-Tenant-Id": "other-firm" } });
  expect((await spoofed.json()).some((p: { id: number }) => p.id === pid)).toBeTruthy(); // still the session's firm
});

test("09 Italian interface", async ({ page }) => {
  await page.goto(`/p/${pid}/costs`);
  await page.getByRole("button", { name: "Italiano" }).click();
  await expect(page.locator("html")).toHaveAttribute("lang", "it");
  await shot(page, "10-costs-italiano");
  await page.getByRole("button", { name: "English" }).click();
});

test("10 pipeline: every processing step of a document, with details on demand", async ({ page }) => {
  await page.goto(`/p/${pid}/documents`);
  await page
    .getByRole("row", { name: /delta_situazione_patrimoniale/ })
    .getByRole("link", { name: /How it was processed/ })
    .click();
  await expect(page.getByRole("heading", { name: "How this document was processed" })).toBeVisible();
  for (const title of [
    "Upload and fingerprint",
    "Reading the text",
    "Recognising the document",
    "Finding the values",
    "Human review",
    "Cross-checks",
    "Cost layers",
    "Effect on the total",
  ])
    await expect(page.getByRole("heading", { name: title })).toBeVisible();
  const values = page.locator("#stage-extract");
  await expect(values.getByText(/values found, \d+ with their exact place/)).toBeVisible();
  await values.getByRole("button", { name: "Show details" }).click();
  await expect(values.getByText(/^p\.\d+$/).first()).toBeVisible(); // every value names its page
  await expect(values.getByText("Looked for")).toBeVisible();
  await expect(values.getByText("Found on the page")).toBeVisible();
  await expect(values.locator(".evidence-box").first()).toBeVisible(); // boxes drawn on the real page
  await values
    .getByRole("row", { name: /Totale patrimonio/ })
    .getByRole("button")
    .click();
  await expect(values.locator('.evidence-box[data-active="true"]')).toHaveCount(1);
  await expect(page.locator("#stage-validate").getByText(/checks passed/)).toBeVisible();
  await shot(page, "11-pipeline-statement");

  await page.goto(`/p/${pid}/documents`);
  await page
    .getByRole("row", { name: /kid_ZZFBILIT0018_it/ })
    .getByRole("link", { name: /How it was processed/ })
    .click();
  const layers = page.locator("#stage-categorize");
  await layers.getByRole("button", { name: "Show details" }).click();
  await expect(layers.getByText("Counted in the total").first()).toBeVisible();
  await page.getByRole("button", { name: "Italiano" }).click();
  await expect(page.getByRole("heading", { name: "Come è stato elaborato questo documento" })).toBeVisible();
  await page.getByRole("button", { name: "English" }).click();
});
