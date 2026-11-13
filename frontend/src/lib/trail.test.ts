import { describe, expect, it } from "vitest";
import { type HistoryEntry, readKind, trailSteps, whyYou } from "./trail";
import type { EvidenceRef, Fact } from "./types";

const base: EvidenceRef = {
  fact_id: 1,
  role: "value",
  document_id: 1,
  filename: "kid.pdf",
  where: "kid.pdf p.1",
  field: "rate_pct",
  label: "Ongoing costs",
  value: "1.08",
  value_extracted: "1.08",
  currency: null,
  status: "extracted",
  review: null,
  page: 1,
  bbox: [50, 341, 545, 350],
  sheet: null,
  cell: null,
  snippet: "Management fees 1.08%",
  engine: "pdfplumber-text",
  confidence: 1,
};

const titles = (e: EvidenceRef, h: HistoryEntry[] = []) => trailSteps(e, h).map((s) => s.title);

describe("readKind", () => {
  it("tells digital text, OCR, spreadsheet and manual entries apart", () => {
    expect(readKind(base)).toBe("text");
    expect(readKind({ ...base, engine: "tesseract-ocr" })).toBe("ocr");
    expect(readKind({ ...base, sheet: "Holdings", cell: "D4", engine: "openpyxl" })).toBe("sheet");
    expect(readKind({ ...base, status: "manual", engine: null })).toBe("manual");
  });
});

describe("trailSteps", () => {
  it("never invents a check: no review data says so, and a person step stays pending", () => {
    expect(titles(base)).toEqual([
      "Read from digital text",
      "No automatic check recorded for this value",
      "Not yet checked by a person",
    ]);
  });

  it("flags low OCR confidence on the read step", () => {
    const [read] = trailSteps({ ...base, engine: "tesseract-ocr", confidence: 0.82 }, []);
    expect(read.title).toBe("Read with OCR from a scanned page");
    expect(read.tone).toBe("warn");
    expect(read.detail).toContain("confidence 82%");
  });

  it("lists readers, checks and reasons from the extraction review", () => {
    const e: EvidenceRef = {
      ...base,
      review: {
        status: "needs_review",
        reasons: ["separator_ambiguous", "flagged_by_critic"],
        engines: ["pdfplumber-text", "rapidocr"],
        checks: [
          { name: "revalidate:reconcile_kid_example", passed: true, detail: "1.08 + 0.18 = 126 on 10'000" },
          { name: "components_sum_to_total", passed: false, detail: "" },
        ],
      },
    };
    const steps = trailSteps(e, []);
    expect(steps.map((s) => s.title)).toEqual([
      "Read from digital text",
      "Read the same by 2 readers",
      "Check passed: reconcile kid example",
      "Check failed: components sum to total",
      "Sent to a person: the thousands separator is ambiguous; flagged by critic",
      "Not yet checked by a person",
    ]);
    expect(steps[2].tone).toBe("ok");
    expect(steps[3].tone).toBe("bad");
  });

  it("shows each person decision with who, when, old and new value and the reason", () => {
    const h: HistoryEntry[] = [
      { action: "accept", old: "1500.00", new: "1500.00", reason: "", user: "massimo", at: "2026-11-12T20:12:00" },
      {
        action: "correct",
        old: "1500.00",
        new: "1600.00",
        reason: "OCR misread",
        user: "massimo",
        at: "2026-11-12T20:14:00",
      },
    ];
    const steps = trailSteps({ ...base, status: "corrected" }, h);
    expect(steps.slice(-2).map((s) => s.title)).toEqual([
      "Accepted by massimo",
      "Corrected by massimo: 1500.00 → 1600.00",
    ]);
    expect(steps.at(-1)?.detail).toBe("OCR misread");
    expect(steps.at(-1)?.at).toBe("2026-11-12T20:14:00");
  });

  it("an accepted review with nothing else says it passed the checks at reading", () => {
    expect(titles({ ...base, review: { status: "accepted" } })[1]).toBe("Passed the checks made while reading");
  });
});

describe("whyYou", () => {
  const fact: Fact = {
    id: 1,
    document_id: 1,
    key: "k",
    kind: "fee_observed",
    field: "amount",
    label: "Custody fee",
    value: "1500.00",
    value_extracted: "1500.00",
    currency: "CHF",
    isin: null,
    fee_code: null,
    fee_label: null,
    measurement: null,
    extra: {},
    evidence: {
      page: 1,
      bbox: [0, 0, 1, 1],
      page_width: 595,
      page_height: 842,
      sheet: null,
      cell: null,
      snippet: "",
      engine: "pdfplumber-text",
      confidence: 1,
    },
    status: "extracted",
  };

  it("is empty for a confident digital value the checks confirmed", () => {
    expect(whyYou({ ...fact, extra: { review: { status: "accepted" } } })).toEqual([]);
  });

  it("names the extraction flags, a scanned page and low confidence", () => {
    const f: Fact = {
      ...fact,
      extra: { review: { status: "needs_review", reasons: ["separator_ambiguous"] } },
      evidence: { ...fact.evidence, engine: "tesseract-ocr", confidence: 0.82 },
    };
    expect(whyYou(f)).toEqual([
      "the thousands separator is ambiguous",
      "scanned page, read with OCR",
      "reading confidence 82%",
    ]);
  });

  it("never asks again once a person handled the value", () => {
    expect(whyYou({ ...fact, status: "accepted", evidence: { ...fact.evidence, confidence: 0.5 } })).toEqual([]);
  });
});
