import { describe, expect, it } from "vitest";
import { MEASUREMENT, chf } from "./format";

describe("chf", () => {
  it("uses the Swiss apostrophe and a true minus sign", () => {
    expect(chf("61449.6", 2)).toBe("CHF 61'449.60");
    expect(chf("-1500")).toBe("−CHF 1'500");
  });
  it("never renders a missing amount as zero", () => {
    expect(chf(null)).toBe("–");
    expect(chf(undefined)).toBe("–");
  });
});

describe("evidence status", () => {
  it("labels unknown as not determined, never as zero", () => {
    expect(MEASUREMENT.unknown.label).toBe("Not determined");
  });
});
