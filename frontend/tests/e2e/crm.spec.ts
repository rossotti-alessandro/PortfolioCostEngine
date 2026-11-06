/**
 * CRM end-to-end: create a contact in the UI, move it through the pipeline to won, and check that the
 * funnel reflects it. Each test uses a unique name and reads counts relative to its own starting point,
 * so it does not depend on test order or on other data in the database.
 */
import { type Page, expect, test } from "@playwright/test";

const HEADERS = { "X-Role": "analyst" }; // the signed-in session (global-setup.ts) decides tenant and user

/** Writes also need the session's CSRF token. */
async function writeHeaders(page: Page) {
  const me = await (await page.request.get("/api/auth/me")).json();
  return { ...HEADERS, "X-CSRF-Token": me.csrf_token as string };
}

async function funnel(page: Page) {
  const r = await page.request.get("/api/crm/funnel", { headers: HEADERS });
  expect(r.ok()).toBeTruthy();
  return r.json();
}

test("create a contact, move it to won, funnel and clients list update", async ({ page }) => {
  const name = `E2E family ${Date.now()}`;
  const before = await funnel(page);

  await page.goto("/crm");
  await expect(page.getByRole("heading", { name: "Clients & pipeline" })).toBeVisible();
  await page.getByRole("button", { name: "New contact" }).first().click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("Name").fill(name);
  await dialog.getByLabel("Estimated assets (CHF)").fill("2'500'000");
  await dialog.getByLabel("Current banks").fill("Bank E2E (Synthetic) SA");
  await dialog.getByRole("button", { name: "Create contact" }).click();

  await expect(page.getByRole("heading", { name })).toBeVisible();
  await expect(page.getByText("CHF 2'500'000")).toBeVisible();

  // Walk the open stages via the stage tracker, then mark as won.
  for (const stage of ["Qualified", "Documents received", "Cost review", "Proposal sent"]) {
    await page.getByRole("button", { name: stage, exact: false }).first().click();
    await page
      .getByRole("dialog")
      .getByRole("button", { name: `Move to ${stage}` })
      .click();
    await expect(page.getByRole("button", { name: stage }).first()).toHaveAttribute("aria-current", "step");
  }
  await page.getByRole("button", { name: "Mark as won" }).click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: /Move to Won/ })
    .click();
  await expect(page.getByText(/Client since/)).toBeVisible();
  await expect(page.getByText("Moved to Won (client)")).toBeVisible();

  const after = await funnel(page);
  expect(after.total).toBe(before.total + 1);
  expect(after.won).toBe(before.won + 1);
  for (const [i, s] of after.stages.entries()) expect(s.reached).toBe(before.stages[i].reached + 1);

  await page.goto("/crm/list");
  await page.getByRole("tab", { name: "Clients" }).click();
  await expect(page.getByRole("cell", { name: new RegExp(name) })).toBeVisible();

  await page.goto("/crm/funnel");
  await expect(page.getByRole("heading", { name: "Conversion funnel" })).toBeVisible();
  await expect(page.getByTestId("bar-won")).toHaveText(String(after.won));
});

test("losing a contact requires a reason and shows up in lost reasons", async ({ page }) => {
  const name = `E2E lost ${Date.now()}`;
  const r = await page.request.post("/api/crm/contacts", {
    headers: await writeHeaders(page),
    data: { name, stage: "qualified" },
  });
  const { id } = await r.json();
  await page.goto(`/crm/c/${id}`);
  await page.getByRole("button", { name: "Mark as lost" }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("Why was it lost?").selectOption("chose_competitor");
  await dialog.getByRole("button", { name: "Move to Lost" }).click();
  await expect(page.getByText("Lost: Chose another manager")).toBeVisible();

  await page.goto("/crm/funnel");
  await page.getByRole("button", { name: "Show details" }).click();
  await expect(page.getByRole("table", { name: "Lost reasons" }).getByText("Chose another manager")).toBeVisible();
});

test("start a cost review from a contact lands on the document upload step", async ({ page }) => {
  const r = await page.request.post("/api/crm/contacts", {
    headers: await writeHeaders(page),
    data: { name: `E2E review ${Date.now()}`, stage: "documents_received" },
  });
  const { id } = await r.json();
  await page.goto(`/crm/c/${id}`);
  await page.getByRole("button", { name: "Start cost review" }).click();
  await expect(page).toHaveURL(/\/p\/\d+\/documents/);
  await page.goto(`/crm/c/${id}`);
  await expect(page.getByRole("list", { name: "Cost review steps" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Continue: Documents" })).toBeVisible();
});

test("home is the pipeline; a seeded client drills down into its cost review", async ({ page }) => {
  await page.request.post("/api/crm/demo/seed", { headers: await writeHeaders(page) });
  await page.goto("/");
  await expect(page).toHaveURL(/\/crm$/);
  await page
    .getByRole("region", { name: "Cost review" })
    .getByRole("link", { name: "Prospect P-1042 (synthetic)" })
    .click();
  const steps = page.getByRole("list", { name: "Cost review steps" });
  await expect(steps).toBeVisible();
  await expect(steps.getByText(/^\d+ documents$/)).toBeVisible();
  await expect(page.getByText("Known annual cost")).toBeVisible();
  await page.getByRole("button", { name: /^Continue: / }).click();
  await expect(page).toHaveURL(/\/p\/\d+\/(documents|review|costs|compare|report)/);
});

test("synthetic CRM seed renders board and funnel with the synthetic banner", async ({ page }) => {
  await page.request.post("/api/crm/demo/seed", { headers: await writeHeaders(page) });
  await page.goto("/crm");
  await expect(page.getByText(/SYNTHETIC demo data/)).toBeVisible();
  await expect(page.getByRole("region", { name: "Lead" })).toBeVisible();
  await page.getByRole("link", { name: "Funnel" }).click();
  await page.getByRole("button", { name: "Show details" }).click();
  await expect(page.getByRole("table", { name: "Funnel by stage" })).toBeVisible();
});

test("the pipeline and funnel render in Italian", async ({ page }) => {
  await page.request.post("/api/crm/demo/seed", { headers: await writeHeaders(page) });
  await page.goto("/crm");
  await page.evaluate(() => localStorage.setItem("feelens.lang", "it"));
  await page.reload();
  await expect(page.getByRole("heading", { name: "Clienti e pipeline" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Analisi dei costi" })).toBeVisible();
  await page.getByRole("link", { name: "Funnel" }).click();
  await expect(page.getByRole("heading", { name: "Funnel di conversione" })).toBeVisible();
  await page.evaluate(() => localStorage.setItem("feelens.lang", "en"));
});
