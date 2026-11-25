import { describe, expect, it } from "vitest";
import { MEASUREMENT, assets, chf, knownCost, moneyOr, savingParts } from "./format";

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

describe("moneyOr", () => {
  it("does not turn a missing stage total into CHF 0", () => {
    expect(moneyOr(undefined, "Not estimated")).toBe("Not estimated");
    expect(moneyOr("", "–")).toBe("–");
    expect(moneyOr("0", "Not estimated")).toBe("CHF 0");
  });
});

describe("knownCost", () => {
  it("does not publish an incomplete zero as a known cost", () => {
    expect(knownCost("0.00", false)).toBeNull();
    expect(knownCost("61449.60", false)).toBe("61449.60");
    expect(knownCost("0", true)).toBe("0");
  });
});

describe("assets", () => {
  it("never shows CHF 0 before a position is valued", () => {
    expect(assets("0", false, "Not valued yet")).toBe("Not valued yet");
    expect(assets("4300000", true, "Not valued yet")).toBe("CHF 4'300'000");
  });
});

describe("evidence status", () => {
  it("labels unknown as not determined, never as zero", () => {
    expect(MEASUREMENT.unknown.label).toBe("Not determined");
  });
});

describe("savingParts", () => {
  it("keeps a real saving and its bound", () => {
    expect(savingParts("6520.10", "at_least")).toEqual({
      saves: true,
      label: "Annual saving",
      prefix: "at least",
      value: "6520.10",
    });
  });
  it("never shows a dearer proposal as a saving, and flips the bound", () => {
    expect(savingParts("-2588.07", "at_least")).toEqual({
      saves: false,
      label: "Proposal costs more per year",
      prefix: "at most",
      value: "2588.07",
    });
    expect(savingParts("-100", "point").prefix).toBe("");
    expect(savingParts("-100", "at_most").prefix).toBe("at least");
  });
});
