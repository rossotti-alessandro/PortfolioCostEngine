import { describe, expect, it } from "vitest";
import { ratioPct } from "./api";

describe("ratioPct", () => {
  it("formats API ratio strings as percentages", () => {
    expect(ratioPct("0.3462")).toBe("34.6%");
    expect(ratioPct("1.0000", 0)).toBe("100%");
  });
  it("shows a missing ratio as not determined, never 0%", () => {
    expect(ratioPct(null)).toBe("Not determined");
  });
});
