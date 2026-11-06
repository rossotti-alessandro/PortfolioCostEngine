import { Page, PageTitle } from "@/components/Shell";
import { Badge, Card, CardHeader, ErrorBox, Spinner, inputCls } from "@/components/ui";
import { api } from "@/lib/api";
import { LAYER, cn } from "@/lib/format";
import { t } from "@/lib/i18n";
import { useQuery } from "@tanstack/react-query";
import { ExternalLink, Search } from "lucide-react";
import { useState } from "react";

const FAMILY: Record<string, string> = {
  holdings: "Holdings",
  cash: "Cash",
  trading: "Trading",
  fees: "Fees",
  contracts: "Contracts & tariffs",
  products: "Products",
  wrappers: "Insurance wrappers",
  credit: "Credit",
  proposal: "Proposal",
  other: "Other",
};

/** Every document type and every fee the system knows: what each proves and cannot prove. */
export default function CataloguePage() {
  const q = useQuery({ queryKey: ["taxonomy"], queryFn: api.taxonomy, staleTime: Number.POSITIVE_INFINITY });
  const [tab, setTab] = useState<"docs" | "fees" | "sources">("docs");
  const [filter, setFilter] = useState("");
  if (q.isLoading) return <Spinner />;
  if (q.error || !q.data) return <ErrorBox error={q.error ?? "no data"} />;
  const f = filter.toLowerCase();
  const match = (...v: string[]) => !f || v.some((x) => x.toLowerCase().includes(f));
  return (
    <Page>
      <PageTitle
        title={t("Data catalogue")}
        subtitle={t(
          "The document types an analyst can upload, the data extracted from each, what each document can and cannot prove, and the fee codes every cost is mapped to.",
        )}
      />
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div className="flex rounded-md border border-line bg-surface p-0.5 text-[13px]" role="tablist">
          {(
            [
              ["docs", t("Document types ({n})", { n: q.data.document_types.length })],
              ["fees", t("Fee codes ({n})", { n: q.data.fees.length })],
              ["sources", t("Official sources ({n})", { n: q.data.public_sources.length })],
            ] as const
          ).map(([k, l]) => (
            <button
              key={k}
              type="button"
              role="tab"
              aria-selected={tab === k}
              onClick={() => setTab(k)}
              className={cn(
                "rounded px-3 py-1.5 font-medium",
                tab === k ? "bg-navy-900 text-white" : "text-muted hover:text-ink",
              )}
            >
              {l}
            </button>
          ))}
        </div>
        <label className="relative w-full max-w-xs">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-subtle" />
          <input
            className={cn(inputCls, "pl-8")}
            placeholder={t("Filter")}
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            aria-label={t("Filter")}
          />
        </label>
      </div>

      {tab === "docs" && (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full text-[13px]">
              <thead className="bg-paper text-left text-[11.5px] uppercase tracking-wide text-subtle">
                <tr>
                  <th className="px-4 py-2 font-medium">{t("Document")}</th>
                  <th className="px-3 py-2 font-medium">{t("Data extracted")}</th>
                  <th className="px-3 py-2 font-medium">{t("Proves")}</th>
                  <th className="px-3 py-2 font-medium">{t("Cannot prove")}</th>
                  <th className="px-4 py-2 font-medium">{t("Status")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line align-top">
                {q.data.document_types
                  .filter((d) => match(d.label_en, d.label_it, d.document_type, d.extract_targets, d.family))
                  .map((d) => (
                    <tr key={d.document_type}>
                      <td className="px-4 py-2.5">
                        <div className="font-medium text-ink">{d.label_en}</div>
                        <div className="text-[12px] text-subtle">
                          {d.label_it} · {FAMILY[d.family] ? t(FAMILY[d.family]) : d.family} ·{" "}
                          {t("priority {n}", { n: d.priority })}
                        </div>
                      </td>
                      <td className="max-w-[280px] px-3 py-2.5 text-[12.5px] text-muted">
                        {d.extract_targets.replaceAll(";", ",")}
                      </td>
                      <td className="px-3 py-2.5 text-[12.5px]">{d.proves}</td>
                      <td className="px-3 py-2.5 text-[12.5px] text-muted">{d.cannot_prove}</td>
                      <td className="px-4 py-2.5">
                        {d.parser ? <Badge tone="green">{t("Parsed in demo")}</Badge> : <Badge>{t("Planned")}</Badge>}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {tab === "fees" && (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full text-[13px]">
              <thead className="bg-paper text-left text-[11.5px] uppercase tracking-wide text-subtle">
                <tr>
                  <th className="px-4 py-2 font-medium">{t("Layer")}</th>
                  <th className="px-3 py-2 font-medium">{t("Fee")}</th>
                  <th className="px-3 py-2 font-medium">{t("Basis")}</th>
                  <th className="px-3 py-2 font-medium">{t("Paid how")}</th>
                  <th className="px-3 py-2 font-medium">{t("Overlaps")}</th>
                  <th className="px-4 py-2 font-medium">{t("Best evidence")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line align-top">
                {q.data.fees
                  .filter((r) => match(r.label_en, r.label_it, r.fee_code, r.layer))
                  .map((r) => (
                    <tr key={r.fee_code}>
                      <td className="px-4 py-2.5">
                        <span className="inline-flex items-center gap-1.5 text-[12.5px]">
                          <span className="h-2.5 w-2.5 rounded-sm" style={{ background: LAYER[r.layer]?.color }} />
                          {LAYER[r.layer] ? t(LAYER[r.layer].short) : r.layer}
                        </span>
                      </td>
                      <td className="px-3 py-2.5">
                        <div className="font-medium">{r.label_en}</div>
                        <div className="font-mono text-[11px] text-subtle">{r.fee_code}</div>
                      </td>
                      <td className="px-3 py-2.5 text-[12.5px] text-muted">
                        {r.basis.replaceAll("_", " ")} · {r.recurrence}
                      </td>
                      <td className="px-3 py-2.5 text-[12.5px] text-muted">{r.economic_incidence}</td>
                      <td className="px-3 py-2.5 text-[12.5px] text-muted">{r.parent_or_overlap || "–"}</td>
                      <td className="px-4 py-2.5 text-[12.5px]">{r.primary_evidence}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {tab === "sources" && (
        <Card>
          <CardHeader
            title={t("Official public documents")}
            subtitle={t(
              "Real published price lists and KIDs, quoted with page and URL. Public list prices are weak evidence for a specific client (status: public tariff) and never replace the client's own documents.",
            )}
          />
          <ul className="divide-y divide-line">
            {q.data.public_sources
              .filter((s) => match(s.issuer, s.document, s.fee_code, s.figure))
              .map((s, i) => (
                <li key={`${s.source_id}-${i}`} className="grid gap-1 px-5 py-3 text-[13px] md:grid-cols-[1fr_1.3fr]">
                  <div>
                    <div className="font-medium text-ink">{s.issuer}</div>
                    <div className="text-[12.5px] text-muted">{s.document}</div>
                    <a
                      href={s.url}
                      target="_blank"
                      rel="noreferrer noopener"
                      className="mt-0.5 inline-flex items-center gap-1 text-[12px] text-teal-700 hover:underline"
                    >
                      {s.page ? t("Source, page {page}", { page: s.page }) : t("Source")}{" "}
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  </div>
                  <div>
                    <div className="flex flex-wrap items-center gap-1.5">
                      <span className="font-mono text-[11px] text-subtle">{s.fee_code}</span>
                      <Badge tone={s.jurisdiction === "CH" ? "navy" : "amber"}>
                        {t("Booked in {code}", { code: s.jurisdiction })}
                      </Badge>
                    </div>
                    <div className="mt-0.5">{s.figure}</div>
                    <div className="text-[12px] text-subtle">{s.note}</div>
                  </div>
                </li>
              ))}
          </ul>
        </Card>
      )}
    </Page>
  );
}
