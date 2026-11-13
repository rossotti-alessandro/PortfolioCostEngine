import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export const cn = (...v: ClassValue[]) => twMerge(clsx(v));

/** Swiss formatting with apostrophe thousands separator. Inputs are decimal strings from the API. */
export function chf(v: string | number | null | undefined, decimals = 0, prefix = "CHF "): string {
  if (v === null || v === undefined || v === "") return "–";
  const n = typeof v === "number" ? v : Number(v);
  if (!Number.isFinite(n)) return "–";
  const s = Math.abs(n)
    .toFixed(decimals)
    .replace(/\B(?=(\d{3})+(?!\d))/g, "'");
  return `${n < 0 ? "−" : ""}${prefix}${s}`;
}

/** Until a position is valued in CHF the total is 0, which would read as an empty portfolio; say so instead. */
export const assets = (total: string, valued: boolean, notValued: string) => (valued ? chf(total) : notValued);

export const num = (v: string | number | null | undefined, decimals = 0) => chf(v, decimals, "");

export function bps(v: string | null | undefined): string {
  if (v === null || v === undefined) return "–";
  return `${Number(v).toFixed(0)} bps`;
}

export function pct(v: string | null | undefined, d = 1): string {
  if (v === null || v === undefined) return "–";
  return `${Number(v).toFixed(d)}%`;
}

/** Cost layers (data/taxonomy/fee_taxonomy.csv). Colours: DESIGN_SYSTEM.md §1 chart palette, via CSS variables. */
export const LAYER: Record<string, { name: string; short: string; color: string }> = {
  L1: { name: "Management / advisory", short: "Service", color: "var(--chart-service)" },
  L2: { name: "Custody & account", short: "Custody", color: "var(--chart-custody)" },
  L3: { name: "Trading & FX", short: "Trading", color: "var(--chart-trading)" },
  L4: { name: "Funds & ETFs (in NAV)", short: "Funds", color: "var(--chart-product)" },
  L5: { name: "Structured products (in price)", short: "Structured", color: "var(--chart-product-tx)" },
  L6: { name: "Implicit execution", short: "Implicit", color: "var(--chart-implicit)" },
  L7: { name: "Insurance wrapper", short: "Wrapper", color: "var(--chart-wrapper)" },
  L8: { name: "Financing", short: "Financing", color: "var(--chart-implicit)" },
  L9: { name: "Taxes on fees & trades", short: "Taxes", color: "var(--chart-taxes)" },
  L10: { name: "One-off & switching", short: "One-off", color: "var(--chart-taxes)" },
  other: { name: "Other", short: "Other", color: "var(--chart-taxes)" },
};

/** Evidence status: DESIGN_SYSTEM.md §1 fixed mapping (label + icon + tone, never colour alone). */
export const MEASUREMENT: Record<string, { label: string; it: string; tone: string; icon: string; help: string }> = {
  observed: {
    label: "Observed",
    it: "Rilevato",
    tone: "green",
    icon: "observed",
    help: "Charged and documented in a bank statement or cost report.",
  },
  contractual: {
    label: "Contractual",
    it: "Contrattuale",
    tone: "navy",
    icon: "contractual",
    help: "Derived from the client's fee agreement or price schedule.",
  },
  public_tariff: {
    label: "Public tariff",
    it: "Tariffa pubblica",
    tone: "violet",
    icon: "contractual",
    help: "Bank's public list price: weak evidence for this client.",
  },
  estimated: {
    label: "Estimated",
    it: "Stimato",
    tone: "amber",
    icon: "estimated",
    help: "Modelled from a dated disclosure (e.g. KID rate × value).",
  },
  illustrative: {
    label: "Illustrative",
    it: "Illustrativo",
    tone: "grey",
    icon: "illustrative",
    help: "Manufacturer example; never a cost actually paid.",
  },
  maximum: {
    label: "Maximum",
    it: "Massimo",
    tone: "grey",
    icon: "illustrative",
    help: "Disclosed upper bound (e.g. 'up to 3%'); not counted.",
  },
  unknown: {
    label: "Not determined",
    it: "Non determinato",
    tone: "red",
    icon: "unknown",
    help: "The cost applies but no evidence yet. Never counted as zero.",
  },
  not_applicable: { label: "Not applicable", it: "Non applicabile", tone: "grey", icon: "na", help: "Does not apply." },
};

export const BOUND_TEXT: Record<string, string> = {
  point: "",
  at_least: "at least",
  at_most: "at most",
  indeterminate: "known costs only",
};

/**
 * How a saving reads to a person. A negative "saving" is never shown as a saving: it becomes
 * "the proposal costs more", and the bound flips with the sign (saving at least -X means
 * the proposal costs at most X more). Untranslated strings; callers pass them through t().
 */
export function savingParts(
  amount: string,
  bound: string,
): { saves: boolean; label: string; prefix: string; value: string } {
  const saves = Number(amount) > 0;
  if (saves || Number(amount) === 0)
    return { saves, label: "Annual saving", prefix: BOUND_TEXT[bound] ?? "", value: amount };
  const flip: Record<string, string> = { at_least: "at_most", at_most: "at_least" };
  return {
    saves: false,
    label: "Proposal costs more per year",
    prefix: BOUND_TEXT[flip[bound] ?? bound] ?? "",
    value: amount.replace(/^-/, ""),
  };
}

export const DOC_TYPES: Record<string, string> = {
  portfolio_statement: "Statement of assets",
  cost_report: "Costs & charges report",
  cash_statement: "Cash statement",
  tariff: "Price schedule",
  kid: "KID (product)",
  termsheet: "Termsheet",
  unknown: "Unclassified",
};
