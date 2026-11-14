import { NotStarted, ReadSummary } from "@/components/ReadSummary";
import { ReviewPoints } from "@/components/ReviewPoints";
import { PageTitle } from "@/components/Shell";
import { TraceDialog, type TraceTarget, sumOf } from "@/components/Trace";
import { ViewMenu, useHidden } from "@/components/ViewMenu";
import { Badge, Button, Card, CardHeader, ErrorBox, Fold, Money, Spinner, StatusBadge } from "@/components/ui";
import { api } from "@/lib/api";
import { LAYER, MEASUREMENT, bps, chf, cn, pct } from "@/lib/format";
import { t, tm } from "@/lib/i18n";
import type { Analysis, Atom, Check, MissingRequest } from "@/lib/types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, ChevronDown, ChevronRight, Copy, Info, XCircle } from "lucide-react";
import { Fragment, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { Bar, BarChart, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

const COST_SECTIONS = [
  { key: "requests", label: "Documents to ask for" },
  { key: "review", label: "Points to review" },
  { key: "layers", label: "Cost by layer" },
  { key: "ledger", label: "Cost ledger" },
  { key: "checks", label: "Validation and reconciliation" },
  { key: "coverage", label: "Evidence coverage by bank" },
  { key: "positions", label: "Positions" },
];

const LAYER_ORDER = ["L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8", "L9", "L10", "other"];

export default function CostsPage() {
  const id = Number(useParams().id);
  const q = useQuery({ queryKey: ["analysis", id], queryFn: () => api.analysis(id) });
  const [trace, setTrace] = useState<TraceTarget | null>(null);
  const [hidden, setHidden] = useHidden("costs");
  if (q.isLoading) return <Spinner label={t("Calculating")} />;
  if (q.error || !q.data) return <ErrorBox error={q.error ?? "no data"} />;
  const a = q.data;
  const L = a.current;
  const pick = (x: Atom) => setTrace({ kind: "atom", atom: x, ledger: L });
  const layer = (k: string) =>
    setTrace(sumOf(LAYER[k] ? t(LAYER[k].name) : k, L.by_layer[k] ?? "0", L, (x) => x.layer === k));
  const show = (k: string) => !hidden.includes(k);
  return (
    <div className="space-y-4">
      <PageTitle
        title={t("Current costs")}
        subtitle={t(
          "Every cost the prospect pays today, across all banks, with its evidence. Amounts are annual and in CHF. Costs we could not verify are listed as not determined and are never counted as zero.",
        )}
        actions={<ViewMenu sections={COST_SECTIONS} hidden={hidden} onChange={setHidden} />}
      />
      {a.holdings.length === 0 ? (
        <NotStarted pid={id} docs={a.documents} />
      ) : (
        <>
          <Answer a={a} onTrace={setTrace} />
          <ReadSummary a={a} />
        </>
      )}

      {show("requests") && <Requests a={a} />}
      {show("review") && (
        <ReviewPoints
          points={a.requests.length ? a.review_points.filter((p) => p.kind !== "not_determined") : a.review_points}
          onOpen={(p) => {
            const x = p.atom_id && L.atoms.find((y) => y.id === p.atom_id);
            if (x) return pick(x);
            const c = a.checks.find((y) => `check:${y.key}` === p.key);
            if (c?.evidence?.length) return setTrace({ kind: "source", title: c.title, evidence: c.evidence });
            const found = a.unused_mentions.filter((m) => p.fact_ids.includes(m.fact_id));
            if (found.length)
              setTrace({
                kind: "source",
                title: t("Found in {file}, not used", { file: p.vars.file }),
                evidence: found,
              });
          }}
        />
      )}
      {a.holdings.length > 0 && show("layers") && <LayerBreakdown a={a} onLayer={layer} />}
      {a.holdings.length > 0 && show("ledger") && (
        <LedgerTable
          a={a}
          onPick={pick}
          onLayer={layer}
          onTotal={() => setTrace(sumOf(t("Known annual cost"), L.total_known, L))}
        />
      )}
      {show("checks") && (
        <Fold
          title={t("Validation and reconciliation")}
          summary={t("{pass} checks passed · {fail} need attention", {
            pass: a.checks.filter((c) => c.status === "pass").length,
            fail: a.checks.filter((c) => c.status === "fail" || c.status === "warn").length,
          })}
        >
          <Checks
            checks={a.checks}
            onOpen={(c) => c.evidence?.length && setTrace({ kind: "source", title: c.title, evidence: c.evidence })}
          />
        </Fold>
      )}
      {a.holdings.length > 0 && show("coverage") && (
        <Fold title={t("Evidence coverage by bank")} summary={t("Strongest evidence for each cost layer")}>
          <CoverageMatrix a={a} />
        </Fold>
      )}
      {a.holdings.length > 0 && show("positions") && (
        <Fold
          title={t("Positions")}
          summary={t("{n} positions from {banks} banks", { n: a.holdings.length, banks: a.institutions.length })}
        >
          <Holdings a={a} />
        </Fold>
      )}
      <TraceDialog root={trace} onClose={() => setTrace(null)} />
    </div>
  );
}

/** The answer first: the known annual cost in one sentence, then what it is made of and how well it is evidenced. */
function Answer({ a, onTrace }: { a: Analysis; onTrace: (x: TraceTarget) => void }) {
  const L = a.current;
  const share = Number(L.verified_share ?? 0);
  const n = L.unknown.length;
  const sum = (title: string, amount: string, f?: (x: Atom) => boolean) => onTrace(sumOf(title, amount, L, f));
  return (
    <Card className="grid lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
      <div className="px-6 py-5">
        <div className="text-[13px] font-medium text-muted">
          {t("Known annual cost today")}
          {!L.is_complete && <span className="text-amber-700"> · {t("at least")}</span>}
        </div>
        <button
          type="button"
          onClick={() => sum(t("Known annual cost"), L.total_known)}
          title={t("How is this calculated?")}
          className="mt-2 block text-left text-[40px] font-semibold leading-none tracking-tight text-navy-900 decoration-dotted decoration-2 underline-offset-8 hover:underline"
        >
          <Money value={chf(L.total_known)} />
        </button>
        <p className="mt-3 max-w-[560px] text-[13.5px] leading-relaxed text-muted">
          {t("{pct} ({bps}) of {aum} across {banks} banks and {positions} positions.", {
            pct: L.total_bps ? pct(String(Number(L.total_bps) / 100), 2) : "–",
            bps: L.total_bps ? bps(L.total_bps) : "–",
            aum: chf(a.aum.total),
            banks: a.institutions.length,
            positions: a.holdings.length,
          })}{" "}
          {n > 0 ? (
            <span className="text-red-700">
              {t(
                "{n} costs are not determined yet, so the real figure is higher. Nothing unknown is counted as zero.",
                {
                  n,
                },
              )}
            </span>
          ) : (
            t("Every cost category is evidenced.")
          )}
        </p>
      </div>
      <dl className="grid grid-cols-1 divide-y divide-line border-t border-line text-[13px] lg:border-l lg:border-t-0">
        <div className="flex items-baseline justify-between gap-3 px-6 py-3.5">
          <dt className="text-muted">{t("Debited from the accounts")}</dt>
          <dd>
            <button
              type="button"
              className="text-[17px] font-semibold text-navy-900 hover:underline"
              onClick={() => sum(t("Debited from account"), L.billed_known, (x) => x.incidence !== "embedded")}
            >
              <Money value={chf(L.billed_known)} />
            </button>
          </dd>
        </div>
        <div className="flex items-baseline justify-between gap-3 px-6 py-3.5">
          <dt className="text-muted">{t("Inside fund and product prices")}</dt>
          <dd>
            <button
              type="button"
              className="text-[17px] font-semibold text-navy-900 hover:underline"
              onClick={() => sum(t("Inside product price (NAV)"), L.embedded_known, (x) => x.incidence === "embedded")}
            >
              <Money value={chf(L.embedded_known)} />
            </button>
          </dd>
        </div>
        <div className="px-6 py-3.5">
          <div className="flex items-baseline justify-between gap-3">
            <dt className="text-muted">{t("Evidence coverage")}</dt>
            <dd className="money num text-[17px] font-semibold text-navy-900">
              {t("{pct}% observed", { pct: (share * 100).toFixed(0) })}
            </dd>
          </div>
          <div className="mt-2 flex h-1.5 overflow-hidden rounded-[2px] bg-paper" aria-hidden>
            <div className="bg-green-700" style={{ width: `${share * 100}%` }} />
            <div className="hatch flex-1" />
          </div>
        </div>
      </dl>
    </Card>
  );
}

/* --------------------------------------------------------------- layer chart + table twin */

function LayerBreakdown({ a, onLayer }: { a: Analysis; onLayer: (k: string) => void }) {
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
                margin={{ left: 0, right: 190, top: 4, bottom: 4 }}
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
                <Bar
                  dataKey="value"
                  radius={[0, 4, 4, 0]}
                  minPointSize={3}
                  isAnimationActive={false}
                  cursor="pointer"
                  onClick={(_d, i) => onLayer(rows[i].key)}
                >
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
                  <td className="num py-1.5 text-right">
                    <button type="button" className="hover:underline" onClick={() => onLayer(r.key)}>
                      {chf(r.value)}
                    </button>
                  </td>
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

function LedgerTable({
  a,
  onPick,
  onLayer,
  onTotal,
}: { a: Analysis; onPick: (x: Atom) => void; onLayer: (k: string) => void; onTotal: () => void }) {
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
              const isOpen = open[g.key] ?? false; // layers folded: totals first, lines on click
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
                    <td className="num px-5 py-2 text-right font-semibold">
                      <button type="button" className="hover:underline" onClick={() => onLayer(g.key)}>
                        {chf(a.current.by_layer[g.key] ?? "0")}
                      </button>
                    </td>
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
                              {tm(x.fee_label)}
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
              <td className="num px-5 py-2.5 text-right">
                <button type="button" className="hover:underline" onClick={onTotal}>
                  {chf(a.current.total_known)}
                </button>
              </td>
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
                label: tm(e.label),
                amount: chf(e.amount),
                reason: tm(e.reason),
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

function Checks({ checks, onOpen }: { checks: Check[]; onOpen: (c: Check) => void }) {
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
              <div className="font-medium text-ink">{tm(c.title)}</div>
              <div className="text-muted">{tm(c.detail)}</div>
              {c.sources && c.sources.length > 0 && (
                <button
                  type="button"
                  onClick={() => onOpen(c)}
                  className="mt-0.5 text-left text-[12px] text-teal-700 hover:underline"
                >
                  {t("Sources: {list}", { list: c.sources.join(" · ") })}
                </button>
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
  const [all, setAll] = useState(false);
  if (!a.requests.length) return null;
  const open = a.requests.filter((r) => r.status === "open");
  // The two biggest gaps carry most of the answer; the rest wait behind "Show all".
  const shown = all ? a.requests : a.requests.slice(0, REQUESTS_SHOWN);
  return (
    <Card>
      <CardHeader
        title={t("Documents to ask for")}
        subtitle={t(
          "Costs that are not determined yet, ranked by how much of the portfolio they affect. Each request names the exact document that would close the gap.",
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
        {shown.map((r) => (
          <div
            key={r.key}
            className={cn(
              "rounded-[var(--radius-card)] border p-3.5",
              r.status === "open" ? "border-amber-700/25 bg-amber-50/60" : "border-line bg-paper opacity-75",
            )}
          >
            <div className="flex items-start justify-between gap-2">
              <div>
                <div className="text-[12.5px] font-medium text-amber-700">
                  {t("Priority {n} · {amount} affected", { n: r.priority, amount: chf(r.assets_affected) })}
                </div>
                <div className="mt-0.5 font-semibold text-navy-900">{tm(r.title)}</div>
              </div>
              {r.status !== "open" && (
                <Badge tone={r.status === "sent" ? "navy" : "grey"}>
                  {r.status === "sent" ? t("Requested") : t("Waived")}
                </Badge>
              )}
            </div>
            <p className="mt-1.5 text-[13px] text-ink">{tm(r.ask_for)}</p>
            <p className="mt-1 text-[12.5px] text-muted">{tm(r.reason)}</p>
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
      {a.requests.length > REQUESTS_SHOWN && (
        <button
          type="button"
          aria-expanded={all}
          onClick={() => setAll(!all)}
          className="w-full border-t border-line px-5 py-2 text-left text-[12.5px] font-medium text-teal-700 hover:bg-paper"
        >
          {all ? t("Show fewer") : t("Show all {n} requests", { n: a.requests.length })}
        </button>
      )}
    </Card>
  );
}

const REQUESTS_SHOWN = 2;

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
