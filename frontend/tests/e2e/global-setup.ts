/** Signs in once with the throwaway E2E account (playwright.config.ts) and saves the session for every test. */
import { request } from "@playwright/test";
import { E2E_ADMIN, E2E_PASSWORD, STORAGE } from "../../playwright.config";

export default async function globalSetup() {
  const ctx = await request.newContext({ baseURL: "http://127.0.0.1:5173" });
  const r = await ctx.post("/api/auth/login", { data: { username: E2E_ADMIN, password: E2E_PASSWORD } });
  if (!r.ok()) throw new Error(`E2E sign-in failed: ${r.status()}`);
  await ctx.storageState({ path: STORAGE });
  await ctx.dispose();
}
