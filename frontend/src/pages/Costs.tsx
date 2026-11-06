import { AtomEvidenceDialog } from "@/components/AtomEvidence";
import { PageTitle } from "@/components/Shell";
import { Badge, Button, Card, CardHeader, ErrorBox, Kpi, Spinner, StatusBadge } from "@/components/ui";
import { api } from "@/lib/api";
import { LAYER, MEASUREMENT, bps, chf, cn, pct } from "@/lib/format";
import { t } from "@/lib/i18n";
import type { Analysis, Atom, Check, MissingRequest } from "@/lib/types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, ChevronDown, ChevronRight, Copy, Info, XCircle } from "lucide-react";
import { Fragment, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { Bar, BarChart, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

const LAYER_ORDER = ["L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8", "L9", "L10", "other"];

export default function CostsPage() {
  const id = Number(useParams().id);
  const q = useQuery({ queryKey: ["analysis", id], queryFn: () => api.analysis(id) });
  const [atom, setAtom] = useState<Atom | null>(null);
  if (q.isLoading) return <Spinner label={t("Calculating")} />;
  if (q.error || !q.data) return <ErrorBox error={q.error ?? "no data"} />;
  const a = q.data;
  const L = a.current;
  return (
    <div className="space-y-4">
      <PageTitle
        title={t("Current costs")}
        subtitle={t(
          "Every cost the prospect pays today, across all banks, with its evidence. Amounts are annual and in CHF. Costs we could not verify are listed as not determined and are never counted as zero.",
        )}
      />
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Kpi
          label={t("Assets reviewed")}
          value={chf(a.aum.total)}
          sub={t("{banks} banks · {positions} positions", {
            banks: a.institutions.length,
            positions: a.holdings.length,
          })}
        />
        <Kpi
          label={t("Known annual cost")}
          value={chf(L.total_known)}
          sub={
            <>
              {L.total_bps ? `${pct(String(Number(L.total_bps) / 100), 2)} (${bps(L.total_bps)})` : "–"}
              {!L.is_complete && <span className="text-amber-700"> · {t("at least, incomplete")}</span>}
            </>
          }
        />
        <Kpi
          label={t("Debited vs inside products")}
          value={`${chf(L.billed_known)}`}
          sub={t("plus {amount} inside fund and product prices", { amount: chf(L.embedded_known) })}
        />
        <CoverageMeter ledger={L} />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.15fr_1fr]">
        <LayerBreakdown a={a} onPick={setAtom} />
        <CoverageMatrix a={a} />
      </div>

      <Requests a={a} />
      <LedgerTable a={a} onPick={setAtom} />
      <Checks checks={a.checks} />
      <Holdings a={a} />
      <AtomEvidenceDialog atom={atom} analysis={a} onClose={() => setAtom(null)} />
    </div>
  );
}

function CoverageMeter({ ledger }: { ledger: Analysis["current"] }) {
  const share = Number(ledger.verified_share ?? 0);
  const n = ledger.unknown.length;
  return (
    <div className="rounded-[var(--radius-card)] border border-line bg-surface px-4 py-3.5">
      <div className="text-[12px] font-medium uppercase tracking-wide text-subtle">{t("Evidence coverage")}</div>
      <div className="num mt-1 text-[22px] font-semibold leading-tight text-navy-900">
        {t("{pct}% observed", { pct: (share * 100).toFixed(0) })}
      </div>
      <div className="mt-2 flex h-1.5 overflow-hidden rounded-full bg-paper" aria-hidden>
        <div className="bg-green-700" style={{ width: `${share * 100}%` }} />
        <div className="hatch flex-1" />
      </div>
      <div className="mt-1.5 text-[12.5px] text-muted">
        {n === 0 ? (
          t("All cost categories evidenced")
        ) : (
          <span className="text-red-700">{t("{n} cost categories not determined", { n })}</span>
        )}
      </div>
    </div>
  );
}

/* --------------------------------------------------------------- layer chart + table twin */

function LayerBreakdown({ a, onPick }: { a: Analysis; onPick: (x: Atom) => void }) {
  const [view, setView] = useState<"chart" | "table">("chart");
  const L = a.current;
  const unknownLayers = new Set(L.atoms.filter((x) => x.role === "unknown").map((x) => x.layer));
  const rows = LAYER_ORDER.filter((k) => Number(L.by_layer[k] ?? 0) > 0 || unknownLayers.has(k)).map((k) => ({
    key: k,
    name: LAYER[k] ? t(LAYER[k].name) : k,
    value: Number(L.by_layer[k] ?? 0),
    unknown: unknownLayers.has(k),
    bps: L.scope_aum ? (Number(L.by_layer[k] ?? 0) / Number(L.scope_aum)) * 10000 : null,
  }));
  return (
    <Card>
      <CardHeader
        title={t("Cost by layer")}
        subtitle={t("Counted once: fees inside a fund's ongoing charge are not added again.")}
        actions={
          <div className="flex rounded-md border border-line p-0.5 text-[12px]" role="tablist">
            {(["chart", "table"] as const).map((v) => (
              <button
                key={v}
                type="button"
                role="tab"
                aria-selected={view === v}
                onClick={() => setView(v)}
                className={cn(
                  "rounded px-2.5 py-1 capitalize",
                  view === v ? "bg-navy-900 text-white" : "text-muted hover:text-ink",
                )}
              >
                {t(v)}
              </button>
            ))}
          </div>
        }
      />
      <div className="p-4">
        {view === "chart" ? (
          <div style={{ height: rows.length * 44 + 20 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={rows}
                layout="vertical"
                margin={{ left: 0, right: 120, top: 4, bottom: 4 }}
                barCategoryGap={10}
              >
                <XAxis type="number" hide />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={190}
                  tickLine={false}
                  axisLine={false}
                  tick={{ fontSize: 12, fill: "var(--color-text)" }}
                />
                <Tooltip
                  cursor={{ fill: "var(--color-surface-muted)" }}
                  formatter={(v: number) => [chf(v), t("Known annual cost")]}
                  contentStyle={{ fontSize: 12, borderRadius: 8, borderColor: "var(--color-border)" }}
                />
                <Bar dataKey="value" radius={[0, 4, 4, 0]} minPointSize={3} isAnimationActive={false}>
                  {rows.map((r) => (
                    <Cell key={r.key} fill={LAYER[r.key]?.color ?? "var(--chart-taxes)"} />
                  ))}
                  <LabelList
                    dataKey="value"
                    position="right"
                    content={(p) => {
                      const {
                        x = 0,
                        y = 0,
                        width = 0,
                        height = 0,
                        index = 0,
                      } = p as { x: number; y: number; width: number; height: number; index: number };
                      const r = rows[index];
                      return (
                        <text
                          x={Number(x) + Number(width) + 8}
                          y={Number(y) + Number(height) / 2 + 4}
                          fontSize={12}
                          fill="var(--color-text)"
                          className="num"
                        >
                          {chf(r.value)}
                          {r.unknown && <tspan fill="var(--color-danger)"> + {t("not determined")}</tspan>}
                        </text>
                      );
                    }}
                  />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <table className="w-full text-[13px]">
            <thead className="text-left text-[12px] text-subtle">
              <tr>
                <th className="py-1.5 font-medium">{t("Layer")}</th>
                <th className="py-1.5 text-right font-medium">{t("CHF / year")}</th>
                <th className="py-1.5 text-right font-medium">bps</th>
                <th className="py-1.5 text-right font-medium">{t("Gaps")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {rows.map((r) => (
                <tr key={r.key}>
                  <td className="py-1.5">{r.name}</td>
                  <td className="num py-1.5 text-right">{chf(r.value)}</td>
                  <td className="num py-1.5 text-right">{r.bps === null ? "–" : r.bps.toFixed(1)}</td>
                  <td className="py-1.5 text-right">
                    {r.unknown ? <Badge tone="red">{t("Not determined")}</Badge> : ""}
                  </td>
                </tr>
              ))}
              <tr className="font-semibold">
                <td className="py-1.5">{t("Total known")}</td>
                <td className="num py-1.5 text-right">{chf(L.total_known)}</td>
                <td className="num py-1.5 text-right">{L.total_bps ? Number(L.total_bps).toFixed(1) : "–"}</td>
                <td />
              </tr>
            </tbody>
          </table>
        )}
        {unknownLayers.size > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5 border-t border-line pt-3 text-[12.5px]">
            <span className="text-muted">{t("Not determined:")}</span>
            {L.atoms
              .filter((x) => x.role === "unknown")
              .map((x) => (
                <button key={x.id} type="button" onClick={() => onPick(x)} className="rounded-full">
                  <Badge tone="red" className="hover:ring-red-700/50">
                    {x.label} · {x.fee_label}
                  </Badge>
                </button>
              ))}
          </div>
        )}
      </div>
    </Card>
  );
}

/* --------------------------------------------------------------- coverage matrix */

const CELL: Record<string, { label: string; cls: string }> = {
  observed: { label: "Observed", cls: "bg-green-100 text-green-700" },
  contractual: { label: "Contract", cls: "bg-navy-100 text-navy-800" },
  public_tariff: { label: "List price", cls: "bg-violet-100 text-violet-700" },
  estimated: { label: "Estimated", cls: "bg-amber-100 text-amber-700" },
  partial: { label: "Partial", cls: "bg-amber-100 text-amber-700" },
  unknown: { label: "Not determined", cls: "hatch text-red-700 font-medium" },
  not_applicable: { label: "n/a", cls: "text-subtle" },
};

function CoverageMatrix({ a }: { a: Analysis }) {
  const layers = ["L1", "L2", "L3", "L4", "L5", "L9"];
  return (
    <Card>
      <CardHeader
        title={t("Evidence coverage by bank")}
        subtitle={t(
          "Strongest evidence for each cost layer. A hatched cell is a gap to close before the comparison is final.",
        )}
      />
      <div className="overflow-x-auto p-4">
        <table className="w-full text-[12.5px]">
          <thead>
            <tr className="text-left text-[11.5px] text-subtle">
              <th className="pb-2 pr-2 font-medium">{t("Bank")}</th>
              {layers.map((l) => (
                <th key={l} className="pb-2 px-1 text-center font-medium">
                  {t(LAYER[l].short)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {a.coverage.map((r) => (
              <tr key={r.institution} className="border-t border-line">
                <td className="py-2 pr-2">
                  <div className="font-medium text-ink">{r.institution}</div>
                  <div className="num text-[11.5px] text-subtle">
                    {chf(r.assets)} · {r.jurisdiction ?? t("jurisdiction ?")}
                  </div>
                </td>
                {layers.map((l) => {
                  const c = CELL[r.cells[l] ?? "not_applicable"];
                  return (
                    <td key={l} className="px-1 py-2">
                      <div className={cn("rounded px-1.5 py-1 text-center text-[11.5px]", c.cls)}>{t(c.label)}</div>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

/* --------------------------------------------------------------- ledger */

function LedgerTable({ a, onPick }: { a: Analysis; onPick: (x: Atom) => void }) {
  const [open, setOpen] = useState<Record<string, boolean>>({});
  const [showAll, setShowAll] = useState(false);
  const groups = useMemo(() => {
    const g: Record<string, Atom[]> = {};
    for (const x of a.current.atoms) {
      if (!showAll && !["counted", "unknown"].includes(x.role ?? "")) continue;
      g[x.layer] = [...(g[x.layer] ?? []), x];
    }
    return LAYER_ORDER.filter((k) => g[k]).map((k) => ({ key: k, atoms: g[k] }));
  }, [a, showAll]);
  return (
    <Card>
      <CardHeader
        title={t("Cost ledger")}
        subtitle={t("Click any line to see the calculation and the highlighted source in the original document.")}
        actions={
          <label className="flex items-center gap-2 text-[12.5px] text-muted">
            <input
              type="checkbox"
              checked={showAll}
              onChange={(e) => setShowAll(e.target.checked)}
              className="accent-teal-700"
            />
            {t("Show linked and non-counted items")}
          </label>
        }
      />
      <div className="overflow-x-auto">
        <table className="w-full text-[13px]">
          <thead className="bg-paper text-left text-[11.5px] uppercase tracking-wide text-subtle">
            <tr>
              <th className="px-5 py-2 font-medium">{t("Item")}</th>
              <th className="px-3 py-2 font-medium">{t("Bank")}</th>
              <th className="px-3 py-2 font-medium">{t("Evidence")}</th>
              <th className="px-3 py-2 text-right font-medium">{t("Rate")}</th>
              <th className="px-5 py-2 text-right font-medium">{t("CHF / year")}</th>
            </tr>
          </thead>
          <tbody>
            {groups.map((g) => {
              const isOpen = open[g.key] ?? true;
              return (
                <Fragment key={g.key}>
                  <tr className="border-t border-line bg-surface hover:bg-paper">
                    <td colSpan={4} className="px-5 py-2 font-semibold text-navy-900">
                      <button
                        type="button"
                        aria-expanded={isOpen}
                        onClick={() => setOpen({ ...open, [g.key]: !isOpen })}
                        className="inline-flex items-center gap-2"
                      >
                        {isOpen ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
                        <span className="h-2.5 w-2.5 rounded-sm" style={{ background: LAYER[g.key]?.color }} />
                        {LAYER[g.key] ? t(LAYER[g.key].name) : g.key}
                      </button>
                    </td>
                    <td className="num px-5 py-2 text-right font-semibold">{chf(a.current.by_layer[g.key] ?? "0")}</td>
                  </tr>
                  {isOpen &&
                    g.atoms.map((x) => {
                      const muted = !["counted", "unknown"].includes(x.role ?? "");
                      return (
                        <tr
                          key={x.id}
                          tabIndex={0}
                          onClick={() => onPick(x)}
                          onKeyDown={(e) => e.key === "Enter" && onPick(x)}
                          className={cn(
                            "cursor-pointer border-t border-line/70 hover:bg-teal-50 focus:bg-teal-50 focus:outline-none",
                            muted && "text-subtle",
                          )}
                        >
                          <td className="py-2 pl-12 pr-3">
                            <div className={cn("font-medium", muted ? "text-subtle" : "text-ink")}>{x.label}</div>
                            <div className="text-[12px] text-muted">
                              {x.fee_label}
                              {x.role === "included_in_parent" &&
                                ` · ${t("included in the fund's ongoing charge, not added")}`}
                              {x.role === "corroborating" &&
                                ` · ${t("second source for the same charge, counted once")}`}
                              {x.role === "not_a_paid_cost" &&
                                ` · ${t("{status}, not a paid cost", { status: t(MEASUREMENT[x.measurement]?.label ?? "").toLowerCase() })}`}
                            </div>
                          </td>
                          <td className="px-3 py-2 text-[12.5px] text-muted">{x.institution ?? "–"}</td>
                          <td className="px-3 py-2">
                            <StatusBadge m={x.measurement} />
                          </td>
                          <td className="num px-3 py-2 text-right text-[12.5px] text-muted">
                            {x.rate_bps ? `${(Number(x.rate_bps) / 100).toFixed(2)}%` : ""}
                          </td>
                          <td className="num px-5 py-2 text-right">
                            {x.amount === null ? (
                              <span className="font-medium text-red-700">{t("Not determined")}</span>
                            ) : muted ? (
                              <s>{chf(x.amount)}</s>
                            ) : (
                              chf(x.amount)
                            )}
                          </td>
                        </tr>
                      );
                    })}
                </Fragment>
              );
            })}
            <tr className="border-t-2 border-navy-900/20 bg-paper font-semibold">
              <td colSpan={4} className="px-5 py-2.5">
                {t("Total known annual cost")}{" "}
                {!a.current.is_complete && (
                  <span className="font-normal text-amber-700">
                    {t("(at least: {n} items not determined)", { n: a.current.unknown.length })}
                  </span>
                )}
              </td>
              <td className="num px-5 py-2.5 text-right">{chf(a.current.total_known)}</td>
            </tr>
          </tbody>
        </table>
      </div>
      {a.comparison_exclusions.length > 0 && (
        <div className="border-t border-line px-5 py-2.5 text-[12.5px] text-muted">
          {a.comparison_exclusions.map((e) => (
            <div key={e.fee_code}>
              <Info className="mr-1 inline h-3.5 w-3.5" />
              {t("{label} {amount} is in this total but excluded from the comparison: {reason}", {
                label: e.label,
                amount: chf(e.amount),
                reason: e.reason,
              })}
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

/* --------------------------------------------------------------- reconciliation checks */

const CHECK_ICON = {
  pass: () => <CheckCircle2 className="h-4 w-4 text-green-700" aria-label={t("Pass")} />,
  warn: () => <AlertTriangle className="h-4 w-4 text-amber-700" aria-label={t("Warning")} />,
  fail: () => <XCircle className="h-4 w-4 text-red-700" aria-label={t("Failed")} />,
  info: () => <Info className="h-4 w-4 text-navy-700" aria-label={t("Information")} />,
};

function Checks({ checks }: { checks: Check[] }) {
  const counts = { pass: 0, warn: 0, fail: 0, info: 0 };
  for (const c of checks) counts[c.status]++;
  return (
    <Card>
      <CardHeader
        title={t("Validation and reconciliation")}
        subtitle={t(
          "Independent checks across documents: totals, dates, duplicates, tariff applicability, contract vs charged, product costs vs bank report.",
        )}
        actions={
          <div className="flex gap-1.5">
            <Badge tone="green">{t("{n} pass", { n: counts.pass })}</Badge>
            {counts.warn > 0 && <Badge tone="amber">{t("{n} warning", { n: counts.warn })}</Badge>}
            {counts.fail > 0 && <Badge tone="red">{t("{n} failed", { n: counts.fail })}</Badge>}
          </div>
        }
      />
      <ul className="divide-y divide-line">
        {checks.map((c) => (
          <li key={c.key} className="flex gap-3 px-5 py-2.5 text-[13px]">
            <span className="mt-0.5 shrink-0">{CHECK_ICON[c.status]()}</span>
            <div className="min-w-0">
              <div className="font-medium text-ink">{c.title}</div>
              <div className="text-muted">{c.detail}</div>
              {c.sources && c.sources.length > 0 && (
                <div className="mt-0.5 text-[12px] text-subtle">
                  {t("Sources: {list}", { list: c.sources.join(" · ") })}
                </div>
              )}
            </div>
          </li>
        ))}
      </ul>
    </Card>
  );
}

/* --------------------------------------------------------------- missing documents */

function letter(a: Analysis, reqs: MissingRequest[]) {
  const byBank: Record<string, MissingRequest[]> = {};
  for (const r of reqs) {
    const k = r.institution ?? t("Product issuer");
    byBank[k] = [...(byBank[k] ?? []), r];
  }
  return Object.entries(byBank)
    .map(([bank, rs]) =>
      t("To: {bank}\nRe: {label}, documents for a cost review\n\nPlease provide:\n{items}\n\nThank you.", {
        bank,
        label: a.prospect.label,
        items: rs.map((r) => `- ${r.ask_for}`).join("\n"),
      }),
    )
    .join("\n\n---\n\n");
}

function Requests({ a }: { a: Analysis }) {
  const qc = useQueryClient();
  const [copied, setCopied] = useState(false);
  const set = useMutation({
    mutationFn: ({ key, status }: { key: string; status: string }) => api.setRequest(a.prospect.id, key, status),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["analysis", a.prospect.id] }),
  });
  if (!a.requests.length) return null;
  const open = a.requests.filter((r) => r.status === "open");
  return (
    <Card>
      <CardHeader
        title={t("What is missing")}
        subtitle={t(
          "Ranked by how much of the portfolio each gap affects. Each request names the exact document that would close it.",
        )}
        actions={
          <Button
            variant="outline"
            size="sm"
            disabled={!open.length}
            onClick={() => {
              navigator.clipboard?.writeText(letter(a, open)).then(() => {
                setCopied(true);
                setTimeout(() => setCopied(false), 1500);
              });
            }}
          >
            <Copy className="h-3.5 w-3.5" /> {copied ? t("Copied") : t("Copy request letter")}
          </Button>
        }
      />
      <div className="grid gap-3 p-4 md:grid-cols-2">
        {a.requests.map((r) => (
          <div
            key={r.key}
            className={cn(
              "rounded-lg border p-3.5",
              r.status === "open" ? "border-amber-700/25 bg-amber-50/60" : "border-line bg-paper opacity-75",
            )}
          >
            <div className="flex items-start justify-between gap-2">
              <div>
                <div className="text-[11.5px] font-semibold uppercase tracking-wide text-amber-700">
                  {t("Priority {n} · {amount} affected", { n: r.priority, amount: chf(r.assets_affected) })}
                </div>
                <div className="mt-0.5 font-semibold text-navy-900">{r.title}</div>
              </div>
              {r.status !== "open" && (
                <Badge tone={r.status === "sent" ? "navy" : "grey"}>
                  {r.status === "sent" ? t("Requested") : t("Waived")}
                </Badge>
              )}
            </div>
            <p className="mt-1.5 text-[13px] text-ink">{r.ask_for}</p>
            <p className="mt-1 text-[12.5px] text-muted">{r.reason}</p>
            <div className="mt-2.5 flex gap-2">
              {r.status === "open" ? (
                <>
                  <Button size="sm" variant="outline" onClick={() => set.mutate({ key: r.key, status: "sent" })}>
                    {t("Mark requested")}
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => set.mutate({ key: r.key, status: "waived" })}>
                    {t("Waive")}
                  </Button>
                </>
              ) : (
                <Button size="sm" variant="ghost" onClick={() => set.mutate({ key: r.key, status: "open" })}>
                  {t("Reopen")}
                </Button>
              )}
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

/* --------------------------------------------------------------- holdings */

function Holdings({ a }: { a: Analysis }) {
  return (
    <Card>
      <CardHeader title={t("Positions")} subtitle={t("As extracted from each bank's statement, valued in CHF.")} />
      <div className="overflow-x-auto">
        <table className="w-full text-[13px]">
          <thead className="bg-paper text-left text-[11.5px] uppercase tracking-wide text-subtle">
            <tr>
              <th className="px-5 py-2 font-medium">{t("Instrument")}</th>
              <th className="px-3 py-2 font-medium">ISIN</th>
              <th className="px-3 py-2 font-medium">{t("Class")}</th>
              <th className="px-3 py-2 font-medium">{t("Bank")}</th>
              <th className="px-3 py-2 text-right font-medium">{t("Weight")}</th>
              <th className="px-5 py-2 text-right font-medium">{t("Value CHF")}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {a.holdings.map((h) => (
              <tr key={h.fact_id}>
                <td className="px-5 py-2 font-medium">{h.name}</td>
                <td className="px-3 py-2 font-mono text-[12px] text-muted">
                  {h.isin ?? "–"} {h.synthetic_isin && <Badge className="ml-1">{t("synthetic")}</Badge>}
                </td>
                <td className="px-3 py-2 text-muted">
                  {h.asset_class}
                  {h.asset_class_inferred && <span className="text-subtle"> ({t("inferred")})</span>}
                </td>
                <td className="px-3 py-2 text-muted">{h.institution}</td>
                <td className="num px-3 py-2 text-right text-muted">
                  {h.weight_pct ? `${Number(h.weight_pct).toFixed(1)}%` : "–"}
                </td>
                <td className="num px-5 py-2 text-right">{chf(h.value)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
