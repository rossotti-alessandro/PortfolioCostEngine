import { describe, expect, it } from "vitest";
import taxonomyCsv from "../../../data/taxonomy/fee_taxonomy.csv?raw";
import { setLang, t, tm } from "./i18n";
import { IT, IT_MESSAGES } from "./it";

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

// One sentence per IT_MESSAGES pattern, written exactly as the backend writes it.
const SERVER_SAMPLES = [
  "AJ Bell: the file holds statements of more than one person",
  "A different client is named from page 16. Their holdings are added together here. Upload only the prospect's pages, or split the file.",
  "A different client is named from page 16",
  "AJ Bell: positions add up to the statement total",
  "Sum of positions 660,273.45 vs printed total 660,273.45 GBP",
  "Sum of positions 1,000.00 vs printed total 1,200.00 CHF (difference 200.00). Check for missing rows or accrued interest",
  "UBS: the statement prints a larger total than the holdings read",
  "Printed total 1,200.00 vs holdings read 1,000.00. Look for cash, policies or accounts that were not read, or a second client in the same file.",
  "UBS: statement total",
  "No printed total found; completeness of the position list cannot be confirmed.",
  "Valuation dates are aligned",
  "Statements have different valuation dates: 2025-12-31, 2026-01-31.",
  "All holdings valued at 2019-04-05.",
  "CH0012345678 appears 2 times",
  "Same instrument in several statements: confirm these are separate holdings, not a consolidated report repeating another bank's positions.",
  "UBS: cost report covers 12 months",
  "Report covers 181 days; amounts are annualised (× 365/181).",
  "tariff.pdf: tariff applicability",
  "No holdings found for this institution, so the booking jurisdiction is unknown.",
  "Julius Baer: price schedule rejected",
  "Tariff issued by a LU entity cannot be applied to an account booked in CH. The document was kept for reference but is not used in any calculation.",
  "Tariff not in force on 2026-01-01 (stale or future source).",
  "UBS: price schedule applies",
  "Issued by a CH entity, account booked in CH, in force on 2025-12-31.",
  "UBS: Custody fee matches the price schedule",
  "Schedule implies 1,200.00 (0.12% of 1,000,000.00); observed 1,200.00",
  "Schedule implies 1,200.00 (0.12% of 1,000,000.00); observed 1,500.00; difference 300.00 — individual conditions or a different fee base?",
  "LU0000000001: product document is older than 18 months",
  "Document dated 2023-01-01; costs may have changed. Request the current version.",
  "UBS: product costs vs the bank's own estimate",
  "KID-based estimate 9,000.00 vs bank-reported 10,000.00 (-10%). The bank figure is used as a cross-check only, never added.",
  "UBS: retrocessions received",
  "UBS reports CHF 1,000.00 of retrocessions paid out of product costs. Not an extra client cost; under Swiss law they generally belong to the client unless validly waived (to verify with counsel).",
  "Duplicate or inclusion check",
  "Cash debits match the annual cost report",
  "Quarterly debits × 4 equal the annual amounts; counted once.",
  "AJ Bell: GBP amounts converted at the printed rate",
  "GBP/CHF 1.1200 as printed on the document. Fees for the year are converted at this valuation-date rate (an approximation for a whole period).",
  "AJ Bell: no GBP/CHF rate on the documents",
  "GBP 660,273.45 could not be converted and is left out of every total. No external rate is fetched.",
  "Custody fee: 1,000.00 does not match Custody fee (report) 1,100.00 (difference 100.00); review which source is correct.",
  "AMF is a sub-component of an unknown parent; parent total still required.",
  "AMF exceeds its inclusive parent OCF; check the disclosure.",
  "Statement of assets for every bank",
  "Statement of assets / portfolio valuation at the same date for each account",
  "Without holdings no cost can be put in proportion to assets.",
  "UBS: price schedule of the Swiss booking entity",
  "Individual fee agreement or current price schedule issued by the CH entity that books the account",
  "The uploaded schedule belongs to another legal entity/jurisdiction.",
  "UBS: annual cost and charges report",
  "Annual report on costs and charges (ex-post) for the last 12 months, or all fee debit advices for the same period, plus the mandate/advisory agreement",
  "No charged fee is documented for UBS (40% of assets). Service, custody and trading costs are shown as UNKNOWN, not zero.",
  "KID for iShares Core S&P 500",
  "Key Information Document (PRIIPs KID or FinSA BIB) for ISIN IE00B5BMR087, exact share class, current version",
  "Product documentation for Private fund A",
  "Embedded costs of a CHF 250,000 position are unknown.",
  "Issuer cost data for Barrier note",
  "Issuer KID or SSPA cost data showing the issue price vs fair value for ISIN CH0000000001",
  "The termsheet does not disclose the issuer margin; this embedded cost stays UNKNOWN.",
  "AJ Bell: GBP/CHF exchange rate at the valuation date",
  "Statement page showing the GBP/CHF rate used for the valuation",
  "Amounts in a foreign currency are not converted with a guessed rate.",
  "Emerging Markets Opportunities Fund A · product costs",
  "Safe Capital (proposal) · management fee (EAM)",
  "Partner custodian (CH) · custody fee",
  "iShares Core S&P 500 · KID cost illustration",
  "iShares Core S&P 500 · Entry charge (maximum)",
  "Swiss VAT 8.1% on management and custody fees",
  "Bank Alpha (Synthetic) · Custody fee",
];

describe("server messages", () => {
  it("translates every server sentence and leaves English alone", () => {
    setLang("it");
    const used = new Set<RegExp>();
    for (const en of SERVER_SAMPLES) {
      const it_ = tm(en);
      expect(it_, en).not.toBe(en);
      expect(it_, en).not.toMatch(/\$\d/);
      for (const [re] of IT_MESSAGES) if (re.test(en)) used.add(re);
    }
    expect(IT_MESSAGES.filter(([re]) => !used.has(re)).map(([re]) => String(re))).toEqual([]);
    expect(
      tm("GBP 660,273.45 could not be converted and is left out of every total. No external rate is fetched."),
    ).toBe(
      "GBP 660,273.45 non può essere convertito ed è escluso da ogni totale. Nessun cambio esterno viene recuperato.",
    );
    expect(tm(SERVER_SAMPLES[1])).toMatch(/^Da pagina 16 compare un altro cliente\. /);
    expect(tm("Something new from the server")).toBe("Something new from the server");
    setLang("en");
    expect(tm(SERVER_SAMPLES[0])).toBe(SERVER_SAMPLES[0]);
  });
});

describe("fee taxonomy labels", () => {
  it("has Italian for every fee label the server can send (data/taxonomy/fee_taxonomy.csv)", () => {
    const [head, ...rows] = taxonomyCsv.trim().split("\n");
    const en = head.split(",").indexOf("label_en");
    const labels = rows.map((r) => r.split(",")[en]).filter(Boolean);
    setLang("it");
    expect(labels.filter((l) => tm(l) === l)).toEqual([]);
    setLang("en");
  });
});
