import { describe, expect, it } from "vitest";
import { setLang, t } from "./i18n";
import { IT } from "./it";

describe("i18n", () => {
  it("falls back to English and interpolates", () => {
    setLang("it");
    expect(t("Demo role")).toBe("Ruolo demo");
    expect(t("No such key {n}", { n: 2 })).toBe("No such key 2");
    setLang("en");
    expect(t("Demo role")).toBe("Demo role");
  });
  it("keeps placeholders in every Italian string", () => {
    for (const [en, it_] of Object.entries(IT)) {
      const ph = (s: string) => (s.match(/\{\w+\}/g) ?? []).sort().join();
      expect(ph(it_), en).toBe(ph(en));
    }
  });
});
