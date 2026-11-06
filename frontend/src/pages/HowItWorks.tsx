import { Page, PageTitle } from "@/components/Shell";
import { Card, CardHeader } from "@/components/ui";
import { t } from "@/lib/i18n";

const STEPS = [
  {
    n: 1,
    t: "Upload",
    d: "Statements, cost reports, cash statements, price lists, KIDs, termsheets. PDF, scans, Excel. SHA-256 fingerprint; nothing leaves the server.",
  },
  {
    n: 2,
    t: "Read",
    d: "Digital text with positions (pdfplumber), OCR for scans (Tesseract, IT/DE/FR/EN), Excel by sheet and cell. Every value keeps page and box.",
  },
  {
    n: 3,
    t: "Classify",
    d: "Document type, bank, booking country, language, date. The analyst can correct the type; the file is re-read.",
  },
  {
    n: 4,
    t: "Review",
    d: "Analyst accepts, corrects (with reason) or rejects each value next to the highlighted source. Every change is logged.",
  },
  {
    n: 5,
    t: "Reconcile",
    d: "Cross-checks between documents (below). Mismatches become warnings or document requests.",
  },
  {
    n: 6,
    t: "Classify costs",
    d: "Each fee mapped to a code and one of ten cost layers, with an evidence status. Unknown stays unknown.",
  },
  {
    n: 7,
    t: "Compare",
    d: "Same assets, same volume, same VAT basis. Saving shown as a bound when costs are missing.",
  },
  {
    n: 8,
    t: "Approve & report",
    d: "Senior reviewer approves the exact figures (snapshot hash). The client PDF carries no internal margin.",
  },
];

const CHECKS = [
  ["Positions add up", "Sum of positions = statement total, per bank.", "Statement of assets"],
  ["Same valuation date", "All bank statements share one valuation date; a difference is flagged.", "Statements"],
  [
    "No double counting",
    "A fund's management fee sits inside its ongoing charge: counted once (1.08%, not 1.83%).",
    "KID",
  ],
  [
    "Same charge, two sources",
    "Quarterly cash debits × 4 = annual cost report line: linked, counted once.",
    "Cash statement + cost report",
  ],
  [
    "Tariff applies",
    "Price list's booking country and dates must match the account (a Luxembourg tariff is rejected for a Swiss account).",
    "Price list",
  ],
  [
    "Contract vs charged",
    "Fee recomputed from the tariff and the assets vs the fee actually debited.",
    "Price list + cost report",
  ],
  ["Product costs", "KID rate × position value vs the bank's own ex-post product cost figure.", "KIDs + cost report"],
  [
    "Missing is not zero",
    "A cost that applies but has no document is shown as not determined and creates a request.",
    "All",
  ],
];

const STATUSES = [
  ["Observed", "Charged and documented (statement, cost report)", "Counted"],
  ["Contractual", "From the client's own fee agreement or tariff", "Counted"],
  ["Public tariff", "From a published list price", "Counted, flagged as weak"],
  ["Estimated", "Rate from a dated disclosure × value (e.g. KID)", "Counted"],
  ["Illustrative / maximum", "Manufacturer example or 'up to' ceiling", "Never counted"],
  ["Not determined", "Applies but no evidence yet", "Never zero; makes totals 'at least'"],
];

/** Workflow and reconciliation explained in one page (also used in the executive deck). */
export default function HowItWorksPage() {
  return (
    <Page>
      <PageTitle
        title={t("How it works")}
        subtitle={t(
          "From a pile of bank documents to a verified, like-for-like cost comparison. No source, no verified figure. Missing is never zero.",
        )}
      />
      <Card className="mb-4">
        <CardHeader title={t("Workflow")} />
        <ol className="grid gap-px overflow-hidden bg-line p-px sm:grid-cols-2 xl:grid-cols-4">
          {STEPS.map((s) => (
            <li key={s.n} className="bg-surface p-4">
              <div className="flex items-center gap-2">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-navy-900 text-[12px] font-semibold text-white">
                  {s.n}
                </span>
                <span className="font-semibold text-navy-900">{t(s.t)}</span>
              </div>
              <p className="mt-1.5 text-[12.5px] leading-relaxed text-muted">{t(s.d)}</p>
            </li>
          ))}
        </ol>
        <div className="border-t border-line px-5 py-3 text-[12.5px] text-muted">
          {t(
            "People decide at steps 4 and 8. Every number on every screen links back to its page and rectangle in the original document.",
          )}
        </div>
      </Card>
      <div className="grid gap-4 xl:grid-cols-[1.4fr_1fr]">
        <Card>
          <CardHeader title={t("Reconciliation checks")} subtitle={t("Run automatically on every change.")} />
          <table className="w-full text-[13px]">
            <tbody className="divide-y divide-line align-top">
              {CHECKS.map(([h, d, src]) => (
                <tr key={h}>
                  <td className="w-44 px-5 py-2.5 font-medium text-ink">{t(h)}</td>
                  <td className="px-3 py-2.5 text-muted">{t(d)}</td>
                  <td className="px-5 py-2.5 text-[12px] text-subtle">{t(src)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
        <Card>
          <CardHeader title={t("Evidence status of every cost")} />
          <table className="w-full text-[13px]">
            <tbody className="divide-y divide-line align-top">
              {STATUSES.map(([h, d, c]) => (
                <tr key={h}>
                  <td className="px-5 py-2.5 font-medium">{t(h)}</td>
                  <td className="px-3 py-2.5 text-muted">{t(d)}</td>
                  <td className="px-5 py-2.5 text-[12px] text-subtle">{t(c)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>
    </Page>
  );
}
