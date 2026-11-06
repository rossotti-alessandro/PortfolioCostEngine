import { AtomEvidenceDialog } from "@/components/AtomEvidence";
import { PageTitle } from "@/components/Shell";
import { Badge, Button, Card, CardHeader, ErrorBox, Field, Kpi, Spinner, StatusBadge, inputCls } from "@/components/ui";
import { api } from "@/lib/api";
import { BOUND_TEXT, LAYER, chf, cn } from "@/lib/format";
import type { Analysis, Atom, Comparison, Ledger, ProposalConfig } from "@/lib/types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, ArrowRight, History, Plus, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

const COMPARE_LAYERS = ["L1", "L2", "L3", "L4", "L5", "L9"];

export default function ComparePage() {
  const pid = Number(useParams().id);
  const q = useQuery({ queryKey: ["analysis", pid], queryFn: () => api.analysis(pid) });
  const [mode, setMode] = useState<"same" | "optimized">("same");
  const [atom, setAtom] = useState<Atom | null>(null);
  if (q.isLoading) return <Spinner label="Calculating" />;
  if (q.error || !q.data) return <ErrorBox error={q.error ?? "no data"} />;
  const a = q.data;
  const sc = mode === "same" ? a.scenarios.same_holdings : a.scenarios.optimized;
  const cmp = sc.comparison;
  const firm = a.proposal_inputs.firm_name;
  return (
    <div className="space-y-4">
      <PageTitle
        title="Compare with the proposal"
        subtitle={`Same assets, same trading volume, same period. The proposal includes the external asset manager fee and the partner custodian's fees.`}
        actions={
          <div
            className="flex rounded-md border border-line bg-surface p-0.5 text-[13px]"
            role="tablist"
            aria-label="Scenario"
          >
            {(
              [
                ["same", "Same holdings"],
                ["optimized", "With product changes"],
              ] as const
            ).map(([k, l]) => (
              <button
                key={k}
                type="button"
                role="tab"
                aria-selected={mode === k}
                onClick={() => setMode(k)}
                className={cn(
                  "rounded px-3 py-1.5 font-medium",
                  mode === k ? "bg-navy-900 text-white" : "text-muted hover:text-ink",
                )}
              >
                {l}
              </button>
            ))}
          </div>
        }
      />
      {!cmp.like_for_like && (
        <div
          className="flex gap-2.5 rounded-lg border border-amber-700/25 bg-amber-50 px-4 py-3 text-[13px] text-amber-700"
          role="note"
        >
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          Not like-for-like: this scenario replaces instruments. The difference mixes fee savings with changes in
          product and risk, and needs suitability review before it is shown to a client.
        </div>
      )}
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Kpi
          label="Today (comparable)"
          value={chf(cmp.current_known)}
          sub={a.scenarios.current_comparable.is_complete ? "complete" : "known costs only, at least"}
        />
        <Kpi
          label={`With ${firm}`}
          value={chf(cmp.proposal_known)}
          sub={sc.ledger.total_bps ? `${Number(sc.ledger.total_bps).toFixed(1)} bps` : undefined}
        />
        <Kpi
          label="Annual saving"
          tone="teal"
          value={
            <>
              <span className="mr-1 text-[14px] font-medium">{BOUND_TEXT[cmp.bound]}</span>
              {chf(cmp.annual_saving)}
            </>
          }
          sub={cmp.annual_saving_bps ? `${Number(cmp.annual_saving_bps).toFixed(1)} bps of assets` : undefined}
        />
        <Kpi
          label="Switching cost"
          value={chf(cmp.migration_one_off)}
          sub={
            cmp.payback_months
              ? `Paid back in ${cmp.payback_months} months · first year ${chf(cmp.first_year_net)}`
              : "Not paid back by the saving"
          }
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.3fr_1fr]">
        <LayerCompare cur={a.scenarios.current_comparable} prop={sc.ledger} cmp={cmp} firm={firm} />
        <Card>
          <CardHeader title="Why the saving is a bound" />
          <ul className="space-y-2 p-5 text-[13px] text-ink">
            {cmp.caveats.map((c) => (
              <li key={c} className="flex gap-2">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-amber-700" />
                {c}
              </li>
            ))}
            {a.comparison_exclusions.map((e) => (
              <li key={e.fee_code} className="flex gap-2">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-navy-700" />
                {e.label} ({chf(e.amount)}) is left out of both sides: {e.reason}
              </li>
            ))}
            <li className="flex gap-2">
              <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-navy-700" />
              Client domicile {a.client_domicile}: Swiss VAT{" "}
              {a.client_domicile === "CH" ? `${a.proposal_inputs.vat_pct}% applies` : "does not apply"} to management
              and custody fees on both sides.
            </li>
            {Object.entries(a.scenarios.same_holdings.migration_items).map(([k, v]) => (
              <li key={k} className="flex gap-2 text-muted">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-line-strong" />
                Switching: {k.replaceAll("_", " ")} {chf(v)}
              </li>
            ))}
          </ul>
        </Card>
      </div>

      {mode === "optimized" && (
        <Card>
          <CardHeader
            title="Instrument changes"
            subtitle={`Rebuild trading cost ${chf(a.scenarios.optimized.rebuild_trading_cost)} is included in switching costs.`}
          />
          <table className="w-full text-[13px]">
            <thead className="bg-paper text-left text-[11.5px] uppercase tracking-wide text-subtle">
              <tr>
                <th className="px-5 py-2 font-medium">From</th>
                <th />
                <th className="px-3 py-2 font-medium">To</th>
                <th className="px-3 py-2 text-right font-medium">Value</th>
                <th className="px-5 py-2 text-right font-medium">Product cost p.a.</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {a.scenarios.optimized.swaps.map((s) => (
                <tr key={s.from}>
                  <td className="px-5 py-2">
                    <div className="font-medium">{s.from_name}</div>
                    <div className="font-mono text-[11.5px] text-subtle">{s.from}</div>
                  </td>
                  <td>
                    <ArrowRight className="h-4 w-4 text-subtle" />
                  </td>
                  <td className="px-3 py-2">
                    <div className="font-medium">{s.to_name}</div>
                    <div className="font-mono text-[11.5px] text-subtle">{s.to}</div>
                  </td>
                  <td className="num px-3 py-2 text-right">{chf(s.value)}</td>
                  <td className="num px-5 py-2 text-right">
                    {s.from_rate_pct ? `${s.from_rate_pct}%` : "not determined"} → {s.to_rate_pct}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      <ProposalLines ledger={sc.ledger} onPick={setAtom} firm={firm} />
      <ProposalEditor a={a} />
      <AtomEvidenceDialog atom={atom} analysis={a} onClose={() => setAtom(null)} />
    </div>
  );
}

/** Paired bars per layer with values printed beside them (the numbers are the table twin). */
function LayerCompare({ cur, prop, cmp, firm }: { cur: Ledger; prop: Ledger; cmp: Comparison; firm: string }) {
  const unknown = new Set(cur.atoms.filter((x) => x.role === "unknown").map((x) => x.layer));
  const rows = COMPARE_LAYERS.map((k) => ({
    k,
    a: Number(cur.by_layer[k] ?? 0),
    b: Number(prop.by_layer[k] ?? 0),
    u: unknown.has(k),
  })).filter((r) => r.a || r.b || r.u);
  const max = Math.max(...rows.flatMap((r) => [r.a, r.b]), 1);
  return (
    <Card>
      <CardHeader
        title="Cost by layer, today vs proposal"
        actions={
          <div className="flex items-center gap-3 text-[12px] text-muted">
            <span className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-sm bg-[var(--chart-taxes)]" /> Today
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-sm bg-teal-700" /> {firm}
            </span>
          </div>
        }
      />
      <table className="w-full text-[13px]">
        <thead className="text-left text-[11.5px] uppercase tracking-wide text-subtle">
          <tr>
            <th className="px-5 pt-3 pb-1 font-medium">Layer</th>
            <th className="w-[38%] px-2 pt-3 pb-1 font-medium" />
            <th className="px-2 pt-3 pb-1 text-right font-medium">Today</th>
            <th className="px-2 pt-3 pb-1 text-right font-medium">Proposal</th>
            <th className="px-5 pt-3 pb-1 text-right font-medium">Difference</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.k} className="border-t border-line/70">
              <td className="px-5 py-2.5">
                {LAYER[r.k].name}
                {r.u && <div className="text-[11.5px] text-red-700">today: part not determined</div>}
              </td>
              <td className="px-2 py-2.5">
                <div className="space-y-1">
                  <div
                    className={cn("h-2 rounded-r", r.u && "hatch")}
                    style={{
                      width: `${(r.a / max) * 100}%`,
                      minWidth: 2,
                      background: r.u ? undefined : "var(--chart-taxes)",
                    }}
                  />
                  <div className="h-2 rounded-r bg-teal-700" style={{ width: `${(r.b / max) * 100}%`, minWidth: 2 }} />
                </div>
              </td>
              <td className="num px-2 py-2.5 text-right">{chf(r.a)}</td>
              <td className="num px-2 py-2.5 text-right">{chf(r.b)}</td>
              <td
                className={cn(
                  "num px-5 py-2.5 text-right font-medium",
                  r.a - r.b >= 0 ? "text-teal-700" : "text-red-700",
                )}
              >
                {chf(r.a - r.b)}
              </td>
            </tr>
          ))}
          <tr className="border-t-2 border-navy-900/20 bg-paper font-semibold">
            <td className="px-5 py-2.5" colSpan={2}>
              Total
            </td>
            <td className="num px-2 py-2.5 text-right">{chf(cmp.current_known)}</td>
            <td className="num px-2 py-2.5 text-right">{chf(cmp.proposal_known)}</td>
            <td className="num px-5 py-2.5 text-right text-teal-700">
              {BOUND_TEXT[cmp.bound] && <span className="mr-1 text-[11.5px] font-normal">{BOUND_TEXT[cmp.bound]}</span>}
              {chf(cmp.annual_saving)}
            </td>
          </tr>
        </tbody>
      </table>
    </Card>
  );
}

function ProposalLines({ ledger, onPick, firm }: { ledger: Ledger; onPick: (a: Atom) => void; firm: string }) {
  const atoms = ledger.atoms.filter((x) => x.role === "counted" || x.role === "unknown");
  return (
    <Card>
      <CardHeader
        title={`${firm}: every line of the proposal`}
        subtitle="Service fees come from the proposal inputs below; product costs reuse the same KID evidence as today."
      />
      <table className="w-full text-[13px]">
        <tbody className="divide-y divide-line">
          {atoms.map((x) => (
            <tr
              key={x.id}
              tabIndex={0}
              onClick={() => onPick(x)}
              onKeyDown={(e) => e.key === "Enter" && onPick(x)}
              className="cursor-pointer hover:bg-teal-50 focus:bg-teal-50 focus:outline-none"
            >
              <td className="px-5 py-2">
                <div className="font-medium">{x.label}</div>
                <div className="font-mono text-[11.5px] text-subtle">{x.formula}</div>
              </td>
              <td className="px-3 py-2 text-[12.5px] text-muted">{LAYER[x.layer]?.short}</td>
              <td className="px-3 py-2">
                <StatusBadge m={x.measurement} />
              </td>
              <td className="num px-5 py-2 text-right">
                {x.amount === null ? <span className="text-red-700">Not determined</span> : chf(x.amount, 2)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}

const NUM_FIELDS: { k: keyof ProposalConfig; label: string; hint?: string }[] = [
  { k: "custody_bps", label: "Custody fee (bps p.a.)", hint: "Partner custodian, on securities" },
  { k: "custody_min", label: "Custody minimum (CHF p.a.)" },
  { k: "brokerage_bps", label: "Brokerage (bps of turnover)" },
  { k: "fx_bps", label: "FX margin (bps of FX volume)" },
  { k: "annual_turnover_chf", label: "Annual turnover (CHF)", hint: "Same volume assumed today and in the proposal" },
  { k: "fx_notional_chf", label: "Annual FX volume (CHF)" },
  { k: "vat_pct", label: "VAT (%)", hint: "Applied only when the client is domiciled in CH" },
];

function ProposalEditor({ a }: { a: Analysis }) {
  const pid = a.prospect.id;
  const qc = useQueryClient();
  const p = useQuery({ queryKey: ["proposal", pid], queryFn: () => api.proposal(pid) });
  const [cfg, setCfg] = useState<ProposalConfig | null>(null);
  useEffect(() => {
    if (p.data) setCfg(p.data.config);
  }, [p.data]);
  const save = useMutation({
    mutationFn: (c: ProposalConfig) => api.saveProposal(pid, c),
    onSuccess: () => qc.invalidateQueries(),
  });
  if (!cfg) return null;
  const set = (k: keyof ProposalConfig, v: unknown) => setCfg({ ...cfg, [k]: v });
  const dirty = JSON.stringify(cfg) !== JSON.stringify(p.data?.config);
  return (
    <Card>
      <CardHeader
        title="Proposal inputs"
        subtitle="Each save creates a new version; the comparison above recalculates from these inputs."
        actions={
          <Button
            variant="primary"
            size="sm"
            disabled={!dirty}
            loading={save.isPending}
            onClick={() => save.mutate(cfg)}
          >
            Save as new version
          </Button>
        }
      />
      {save.error && <ErrorBox error={save.error} />}
      <div className="grid gap-6 p-5 lg:grid-cols-[1fr_1fr_260px]">
        <div className="space-y-3">
          <Field label="Firm name (shown to the client)">
            <input className={inputCls} value={cfg.firm_name} onChange={(e) => set("firm_name", e.target.value)} />
          </Field>
          <Field label="Custodian">
            <input className={inputCls} value={cfg.custodian} onChange={(e) => set("custodian", e.target.value)} />
          </Field>
          <div>
            <div className="flex items-center justify-between">
              <span className="text-[12.5px] font-medium">Management fee tiers</span>
              <select
                className="h-7 rounded border border-line-strong bg-surface px-1.5 text-[12px]"
                value={cfg.eam_tier_method}
                onChange={(e) => set("eam_tier_method", e.target.value)}
                aria-label="Tier method"
              >
                <option value="marginal">Marginal (each band at its rate)</option>
                <option value="whole_base">Whole base (one rate for all)</option>
              </select>
            </div>
            <div className="mt-1.5 space-y-1.5">
              {cfg.eam_tiers.map(([up, rate], i) => (
                <div key={`${i}-${up}`} className="flex items-center gap-2 text-[12.5px]">
                  <span className="w-12 text-muted">{i === 0 ? "Up to" : up === null ? "Above" : "Up to"}</span>
                  <input
                    className={cn(inputCls, "h-8")}
                    placeholder="no limit"
                    value={up ?? ""}
                    aria-label="Band upper limit CHF"
                    onChange={(e) =>
                      set(
                        "eam_tiers",
                        cfg.eam_tiers.map((t, j) =>
                          j === i ? [e.target.value === "" ? null : e.target.value, t[1]] : t,
                        ),
                      )
                    }
                  />
                  <input
                    className={cn(inputCls, "h-8 w-24")}
                    value={rate}
                    aria-label="Rate bps"
                    onChange={(e) =>
                      set(
                        "eam_tiers",
                        cfg.eam_tiers.map((t, j) => (j === i ? [t[0], e.target.value] : t)),
                      )
                    }
                  />
                  <span className="text-muted">bps</span>
                  {cfg.eam_tiers.length > 1 && (
                    <button
                      type="button"
                      aria-label="Remove band"
                      className="text-subtle hover:text-red-700"
                      onClick={() =>
                        set(
                          "eam_tiers",
                          cfg.eam_tiers.filter((_, j) => j !== i),
                        )
                      }
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>
              ))}
              <Button
                variant="ghost"
                size="sm"
                onClick={() =>
                  set("eam_tiers", [
                    ...cfg.eam_tiers.slice(0, -1),
                    ["", cfg.eam_tiers.at(-1)?.[1] ?? "50"],
                    [null, "40"],
                  ])
                }
              >
                <Plus className="h-3.5 w-3.5" /> Add band
              </Button>
            </div>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          {NUM_FIELDS.map((f) => (
            <Field key={f.k} label={f.label} hint={f.hint}>
              <input
                className={inputCls}
                inputMode="decimal"
                value={String(cfg[f.k])}
                onChange={(e) => set(f.k, e.target.value)}
              />
            </Field>
          ))}
        </div>
        <div>
          <div className="flex items-center gap-1.5 text-[12.5px] font-medium">
            <History className="h-3.5 w-3.5" /> Versions
          </div>
          <ul className="mt-2 space-y-1.5 text-[12.5px]">
            {(p.data?.history ?? []).length === 0 && <li className="text-subtle">Default inputs, not yet saved.</li>}
            {p.data?.history.map((h) => (
              <li key={h.version} className="rounded-md bg-paper px-2.5 py-1.5">
                <div className="flex justify-between">
                  <span className="font-medium">v{h.version}</span>
                  <span className="text-subtle">{h.at.slice(0, 16).replace("T", " ")}</span>
                </div>
                <div className="text-muted">
                  {h.user} · saving {BOUND_TEXT[h.summary.bound] ?? ""} {chf(h.summary.annual_saving)}
                </div>
              </li>
            ))}
          </ul>
          <Badge className="mt-3">Internal costs and margin: see Internal economics</Badge>
        </div>
      </div>
    </Card>
  );
}
