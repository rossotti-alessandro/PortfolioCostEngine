import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { defineConfig } from "@playwright/test";

// Each run gets an empty database and upload store, so tests never see earlier data.
const dataDir = process.env.PCE_E2E_DATA_DIR ?? mkdtempSync(join(tmpdir(), "feelens-e2e-"));
process.env.PCE_E2E_DATA_DIR = dataDir; // workers re-import this file: keep one directory per run

// Throwaway account for the local E2E server only; plain-HTTP cookies because the dev server has no TLS.
export const E2E_ADMIN = "e2e.admin";
export const E2E_PASSWORD = "e2e-only-password-not-a-secret";
export const STORAGE = join(dataDir, "e2e-session.json");

export default defineConfig({
  testDir: "tests/e2e",
  timeout: 120_000,
  expect: { timeout: 20_000 },
  fullyParallel: false,
  workers: 1,
  reporter: [["list"], ["html", { open: "never", outputFolder: "../artifacts/e2e/report" }]],
  outputDir: "../artifacts/e2e/results",
  globalSetup: "./tests/e2e/global-setup.ts",
  use: {
    baseURL: "http://127.0.0.1:5173",
    storageState: STORAGE,
    viewport: { width: 1440, height: 900 },
    trace: "off",
  },
  webServer: [
    {
      command: "uv run --project ../backend uvicorn pce.api:app --host 127.0.0.1 --port 8000",
      url: "http://127.0.0.1:8000/api/health",
      env: {
        PCE_DATA_DIR: dataDir,
        PCE_ADMIN_USERNAME: E2E_ADMIN,
        PCE_ADMIN_PASSWORD: E2E_PASSWORD,
        PCE_COOKIE_SECURE: "0",
      },
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: "pnpm exec vite --host 127.0.0.1 --port 5173 --strictPort",
      url: "http://127.0.0.1:5173",
      reuseExistingServer: false,
      timeout: 60_000,
    },
  ],
});
