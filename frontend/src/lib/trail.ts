/** Decision trail of one extracted value: how it was read, what the automatic checks said, what a person did.
 *  Pure: built only from what the API returned, so a step that has no data says so instead of being invented. */
import { t } from "./i18n";
import type { EvidenceRef, ExtractionReview, Fact } from "./types";

export interface HistoryEntry {
  action: string;
  old: string | null;
  new: string | null;
  reason: string;
  user: string;
  at: string;
}

export type StepKind = "read" | "check" | "flag" | "none" | "person" | "pending";
export type Tone = "neutral" | "ok" | "warn" | "bad";

export interface TrailStep {
  kind: StepKind;
  title: string;
  detail?: string;
  tone: Tone;
  at?: string;
}

const OCR = /ocr|tesseract|paddle|doctr|rapid/i;

export function readKind(e: EvidenceRef): "text" | "ocr" | "sheet" | "manual" {
  if (e.status === "manual" && !e.engine) return "manual";
  if (e.sheet || e.cell) return "sheet";
  return e.engine && OCR.test(e.engine) ? "ocr" : "text";
}

const READ_TITLE = {
  text: "Read from digital text",
  ocr: "Read with OCR from a scanned page",
  sheet: "Read from a spreadsheet cell",
  manual: "Entered by a person",
};

// Plain wording for the extraction's reason codes; an unknown code still reads as words.
const REASON: Record<string, string> = {
  zero_in_text: "the text shows zero",
  amount_implausible: "the amount looks implausible",
  separator_ambiguous: "the thousands separator is ambiguous",
  ocr_low_confidence: "OCR confidence is low",
  rate_out_of_range: "the rate is outside the usual range",
  not_confirmed: "no second reader confirmed it",
  engines_disagree: "the readers disagree",
  linkers_disagree: "label and value links disagree",
};

const words = (code: string) => code.replace(/^[a-z]+:/, "").replace(/_/g, " ");

export function reasonText(code: string): string {
  if (REASON[code]) return t(REASON[code]);
  if (code.startsWith("flagged_by_")) return t("flagged by {who}", { who: words(code.slice(11)) });
  return words(code);
}

function readStep(e: EvidenceRef): TrailStep {
  const kind = readKind(e);
  const conf = e.confidence === null ? null : Math.round(e.confidence * 100);
  const parts = [
    e.engine,
    conf !== null && kind !== "manual" ? t("confidence {pct}%", { pct: conf }) : null,
    e.where,
  ].filter(Boolean);
  return {
    kind: "read",
    title: t(READ_TITLE[kind]),
    detail: parts.join(" · "),
    tone: conf !== null && conf < 90 ? "warn" : "neutral",
  };
}

function machineSteps(e: EvidenceRef): TrailStep[] {
  const r = e.review;
  if (!r) return [{ kind: "none", title: t("No automatic check recorded for this value"), tone: "neutral" }];
  const out: TrailStep[] = [];
  const engines = r.engines ?? [];
  if (engines.length > 1)
    out.push({
      kind: "check",
      title: t("Read the same by {n} readers", { n: engines.length }),
      detail: engines.join(", "),
      tone: "ok",
    });
  for (const c of r.checks ?? [])
    out.push({
      kind: "check",
      title: c.passed
        ? t("Check passed: {name}", { name: words(c.name) })
        : t("Check failed: {name}", { name: words(c.name) }),
      detail: c.detail || undefined,
      tone: c.passed ? "ok" : "bad",
    });
  for (const a of r.alternatives ?? [])
    out.push({
      kind: "flag",
      title: t("Another reader saw {value}", { value: a.value ?? t("no value") }),
      detail: a.engine,
      tone: "warn",
    });
  if (r.status === "needs_review")
    out.push({
      kind: "flag",
      title: t("Sent to a person: {reasons}", { reasons: (r.reasons ?? []).map(reasonText).join("; ") }),
      tone: "warn",
    });
  if (!out.length) out.push({ kind: "check", title: t("Passed the checks made while reading"), tone: "ok" });
  return out;
}

const PERSON: Record<string, string> = {
  accept: "Accepted by {user}",
  correct: "Corrected by {user}: {old} → {new}",
  reject: "Rejected by {user}",
  reset: "Reset to the value read, by {user}",
};

function personSteps(e: EvidenceRef, history: HistoryEntry[]): TrailStep[] {
  if (history.length)
    return history.map((h) => ({
      kind: "person",
      title: t(PERSON[h.action] ?? h.action, { user: h.user, old: h.old ?? "–", new: h.new ?? "–" }),
      detail: h.reason || undefined,
      tone: h.action === "reject" ? "bad" : h.action === "reset" ? "neutral" : "ok",
      at: h.at,
    }));
  if (e.status === "extracted") return [{ kind: "pending", title: t("Not yet checked by a person"), tone: "warn" }];
  return [{ kind: "person", title: t("Checked by a person"), tone: "ok" }];
}

export function trailSteps(e: EvidenceRef, history: HistoryEntry[]): TrailStep[] {
  return [readStep(e), ...machineSteps(e), ...personSteps(e, history)];
}

/** Why a value read from a document needs a person: the extraction's own flags, a scanned page, low confidence.
 *  Empty when the automatic checks are enough. A value a person already handled never needs them again. */
export function whyYou(f: Fact): string[] {
  if (f.status !== "extracted") return [];
  const out: string[] = [];
  const r = f.extra?.review as ExtractionReview | null | undefined;
  if (r?.status === "needs_review")
    out.push(...(r.reasons?.length ? r.reasons.map(reasonText) : [t("the automatic checks could not confirm it")]));
  if (OCR.test(f.evidence.engine)) out.push(t("scanned page, read with OCR"));
  if (f.evidence.confidence < 0.9)
    out.push(t("reading confidence {pct}%", { pct: Math.round(f.evidence.confidence * 100) }));
  return [...new Set(out)];
}
