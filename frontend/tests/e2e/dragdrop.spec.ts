import { type Page, expect, test } from "@playwright/test";

/** Drag and drop (SC-8.26): files dropped anywhere on Documents, CRM cards dragged between stages. SYNTHETIC data. */

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

test("files dragged over Documents show the drop overlay; a wrong type is refused at once", async ({ page }) => {
  const pid = await demoProspect(page);
  await page.goto(`/p/${pid}/documents`);
  await expect(page.getByRole("heading", { name: "Uploaded documents" })).toBeVisible();
  const dt = await page.evaluateHandle(() => {
    const d = new DataTransfer();
    d.items.add(new File(["SYNTHETIC notes"], "notes_synthetic.txt", { type: "text/plain" }));
    return d;
  });
  await page.dispatchEvent("main", "dragenter", { dataTransfer: dt });
  await expect(page.getByText("Drop to add 1 file to this cost review")).toBeVisible();
  await page.dispatchEvent("main", "drop", { dataTransfer: dt });
  await expect(page.getByText("Drop to add 1 file to this cost review")).toHaveCount(0);
  await expect(page.getByText("Only PDF or XLSX files can be read")).toBeVisible();
});

test("a CRM card dragged to another stage moves there", async ({ page }) => {
  await page.goto("/crm");
  await expect(page.getByRole("heading", { name: "Clients & pipeline" })).toBeVisible();
  const name = `E2E drag ${Date.now()}`;
  await page.getByRole("button", { name: "New contact" }).first().click();
  await page.getByRole("dialog").getByLabel("Name").fill(name);
  await page.getByRole("dialog").getByRole("button", { name: "Create contact" }).click();
  await expect(page.getByRole("heading", { name })).toBeVisible();
  await page.goto("/crm");
  const card = page.getByRole("listitem").filter({ hasText: name });
  const target = page.getByRole("region", { name: "Qualified" });
  // Synthetic drag events: a long Lead column scrolls the card out of reach of a pointer drag.
  const dt = await page.evaluateHandle(() => new DataTransfer());
  await card.dispatchEvent("dragstart", { dataTransfer: dt });
  await target.dispatchEvent("dragover", { dataTransfer: dt });
  await target.dispatchEvent("drop", { dataTransfer: dt });
  await card.dispatchEvent("dragend", { dataTransfer: dt });
  await expect(target.getByRole("listitem").filter({ hasText: name })).toBeVisible();
  await expect(page.getByText(`${name} moved to Qualified`)).toBeAttached();
});
