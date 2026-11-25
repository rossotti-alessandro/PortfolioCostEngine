/** Labels and queue rules for the check-values screen. English strings are i18n keys. */

import { num } from "@/lib/format";
import { t } from "@/lib/i18n";
import { whyYou } from "@/lib/trail";
import type { Fact } from "@/lib/types";

export const KIND_LABEL: Record<string, string> = {
  position: "Positions",
  doc_total: "Totals",
  fee_observed: "Fees charged",
  cash_debit: "Fee debits",
  fee_rule: "Contract terms",
  product_cost: "Product costs",
  reported: "Reported by bank",
  meta: "Document details",
};

export const STATUS_TONE: Record<string, string> = {
  extracted: "grey",
  accepted: "teal",
  corrected: "violet",
  rejected: "red",
  manual: "navy",
};

/** The queue: what needs a person first, what the checks confirmed, what a person already handled. */
export const QUEUE = [
  { key: "needs", label: "Needs you", test: (f: Fact) => whyYou(f).length > 0 },
  { key: "auto", label: "Confirmed by checks", test: (f: Fact) => f.status === "extracted" && !whyYou(f).length },
  { key: "person", label: "Checked by a person", test: (f: Fact) => f.status !== "extracted" },
  { key: "all", label: "All", test: () => true },
] as const;

export type QueueKey = (typeof QUEUE)[number]["key"];

/** The amount the analyst is checking, formatted the same way as the rest of the app. */
export function displayValue(f: Fact): string {
  if (f.value === null) return f.measurement === "unknown" ? t("not disclosed") : String(f.extra?.entity ?? "") || "–";
  if (f.field === "rate_pct") return `${f.value}%`;
  return `${f.currency ? `${f.currency} ` : ""}${num(f.value, 2)}`;
}
