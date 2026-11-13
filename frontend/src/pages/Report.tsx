import { NotStarted, ReadSummary } from "@/components/ReadSummary";
import { PageTitle } from "@/components/Shell";
import { Badge, Button, Card, CardHeader, ErrorBox, Money, Spinner, StatGrid, inputCls } from "@/components/ui";
import { api, getRole } from "@/lib/api";
import { LAYER, chf, savingParts } from "@/lib/format";
import { getLang, t } from "@/lib/i18n";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Download, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { useParams } from "react-router-dom";

/** Client-safe preview. Uses only /analysis (internal economics are stripped server-side). */
export default function ReportPage() {
  const pid = Number(useParams().id);
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["analysis", pid], queryFn: () => api.analysis(pid) });
  const audit = useQuery({ queryKey: ["audit", pid], queryFn: () => api.audit(pid) });
  const [note, setNote] = useState("");
  const [dl, setDl] = useState<"en" | "it" | null>(null);
  const approve = useMutation({ mutationFn: () => api.approve(pid, note), onSuccess: () => qc.invalidateQueries() });
  if (q.isLoading) return <Spinner />;
  if (q.error || !q.data) return <ErrorBox error={q.error ?? "no data"} />;
  const a = q.data;
  const s = a.scenarios.same_holdings;
  const cur = a.scenarios.current_comparable;
  const sv = savingParts(s.comparison.annual_saving, s.comparison.bound);
  const firm = a.proposal_inputs.firm_name;
  const approved = !!a.approval?.valid;
  const layers = ["L1", "L2", "L3", "L4", "L5", "L9"].filter(
    (k) => Number(cur.by_layer[k] ?? 0) || Number(s.ledger.by_layer[k] ?? 0),
  );
  return (
    <div className="space-y-4">
      <PageTitle
        title={t("Client report")}
        subtitle={t(
          "What the client receives: computed figures only, each with its evidence status. Internal margin and analyst notes are never included.",
        )}
        actions={
          a.holdings.length > 0 && (
            <span className="flex gap-2">
              {(["en", "it"] as const).map((l) => (
                <Button
                  key={l}
                  variant={l === getLang() ? "primary" : "outline"}
                  loading={dl === l}
                  onClick={async () => {
                    setDl(l);
                    try {
                      await api.downloadReport(pid, a.prospect.code, l);
                    } finally {
                      setDl(null);
                    }
                  }}
                >
                  <Download className="h-4 w-4" /> {l === "en" ? t("PDF in English") : t("PDF in Italian")}
                </Button>
              ))}
            </span>
          )
        }
      />
      {a.holdings.length === 0 ? (
        <NotStarted pid={pid} docs={a.documents.length} />
      ) : (
        <div className="grid gap-4 xl:grid-cols-[1fr_320px]">
          <Card className="overflow-hidden">
            <div className="border-b border-line bg-navy-900 px-6 py-4 text-white">
              <div className="text-[11.5px] uppercase tracking-wider text-white/60">{firm}</div>
              <div className="mt-0.5 text-lg font-semibold">
                {t("Portfolio cost review · {label}", { label: a.prospect.label })}
              </div>
              <div className="mt-1 text-[12.5px] text-white/70">
                {approved
                  ? t("Approved by {user} on {date}", {
                      user: a.approval?.user ?? "",
                      date: a.approval?.at.slice(0, 10) ?? "",
                    })
                  : t("Draft, not approved for client use")}
              </div>
            </div>
            <div className="space-y-5 p-6">
              <ReadSummary a={a} />
              <StatGrid className="grid-cols-[repeat(auto-fit,minmax(180px,1fr))]">
                <Fig
                  label={t("Today, known annual cost")}
                  value={chf(cur.total_known)}
                  sub={cur.is_complete ? undefined : t("at least; some costs unknown")}
                />
                <Fig label={t("With {firm}", { firm })} value={chf(s.ledger.total_known)} />
                <Fig label={t(sv.label)} prefix={t(sv.prefix)} value={chf(sv.value)} accent={sv.saves} />
              </StatGrid>
              <table className="w-full text-[13px]">
                <thead className="text-left text-[11.5px] uppercase tracking-wide text-subtle">
                  <tr className="border-b border-line">
                    <th className="py-1.5 font-medium">{t("Cost layer")}</th>
                    <th className="py-1.5 text-right font-medium">{t("Today")}</th>
                    <th className="py-1.5 text-right font-medium">{firm}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {layers.map((k) => (
                    <tr key={k}>
                      <td className="py-1.5">{t(LAYER[k].name)}</td>
                      <td className="num py-1.5 text-right">{chf(cur.by_layer[k] ?? "0")}</td>
                      <td className="num py-1.5 text-right">{chf(s.ledger.by_layer[k] ?? "0")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div>
                <div className="text-[13px] font-semibold text-navy-900">{t("Not yet verified")}</div>
                <ul className="mt-1 space-y-0.5 text-[13px] text-muted">
                  {cur.atoms
                    .filter((x) => x.role === "unknown")
                    .map((x) => (
                      <li key={x.id}>
                        {x.label}: {x.fee_label}{" "}
                        <span className="text-red-700">({t("not determined, not counted as zero")})</span>
                      </li>
                    ))}
                </ul>
              </div>
              <ul className="space-y-0.5 text-[12.5px] text-subtle">
                {s.comparison.caveats.map((c) => (
                  <li key={c}>{c}</li>
                ))}
                <li>
                  {s.comparison.payback_months
                    ? t("Switching costs {amount}, paid back in {months} months.", {
                        amount: chf(s.comparison.migration_one_off),
                        months: s.comparison.payback_months,
                      })
                    : t("Switching costs {amount}.", { amount: chf(s.comparison.migration_one_off) })}
                </li>
              </ul>
            </div>
          </Card>
          <div className="space-y-4">
            <Card>
              <CardHeader title={t("Approval")} />
              <div className="space-y-3 p-4 text-[13px]">
                {approved ? (
                  <div className="flex items-start gap-2 text-green-700">
                    <CheckCircle2 className="mt-0.5 h-4 w-4" />
                    <div>
                      {t(
                        "Approved by {user}. Any later change to documents, reviews or inputs invalidates the approval.",
                        { user: a.approval?.user ?? "" },
                      )}
                      <div className="mt-1 font-mono text-[11px] text-subtle">
                        {t("snapshot {hash}", { hash: a.snapshot_hash.slice(0, 12) })}
                      </div>
                    </div>
                  </div>
                ) : a.approval ? (
                  <Badge tone="amber">{t("Earlier approval no longer valid: figures changed")}</Badge>
                ) : (
                  <p className="text-muted">
                    {t("A senior reviewer approves the exact figures shown (snapshot {hash}).", {
                      hash: a.snapshot_hash.slice(0, 12),
                    })}
                  </p>
                )}
                {getRole() === "senior" ? (
                  <>
                    <input
                      className={inputCls}
                      placeholder={t("Approval note (optional)")}
                      value={note}
                      onChange={(e) => setNote(e.target.value)}
                    />
                    <Button
                      className="w-full"
                      onClick={() => approve.mutate()}
                      loading={approve.isPending}
                      disabled={approved}
                    >
                      <ShieldCheck className="h-4 w-4" /> {t("Approve for client use")}
                    </Button>
                    {approve.error && <ErrorBox error={approve.error} />}
                  </>
                ) : (
                  <p className="text-[12.5px] text-subtle">
                    {t("Only a senior reviewer can approve. Switch the demo role in the account menu.")}
                  </p>
                )}
              </div>
            </Card>
            <Card>
              <CardHeader title={t("Audit trail")} />
              <ol className="max-h-[360px] space-y-2 overflow-auto p-4 text-[12.5px]">
                {(audit.data ?? []).map((e, i) => (
                  <li key={`${e.at}-${i}`} className="border-l-2 border-line pl-3">
                    <div className="font-medium text-ink">{e.action.replaceAll(".", " ")}</div>
                    <div className="text-subtle">
                      {e.user} · {e.at.slice(0, 16).replace("T", " ")}
                    </div>
                  </li>
                ))}
              </ol>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}

function Fig({
  label,
  value,
  prefix,
  sub,
  accent,
}: { label: string; value: string; prefix?: string; sub?: string; accent?: boolean }) {
  return (
    <div className="rounded-[var(--radius-card)] border border-line px-4 py-3">
      <div className="truncate text-[12px] text-muted" title={label}>
        {label}
      </div>
      <div className={`mt-1.5 text-[22px] font-semibold leading-none ${accent ? "text-teal-700" : "text-navy-900"}`}>
        {prefix && <span className="mr-1.5 text-[13px] font-medium">{prefix}</span>}
        <Money value={value} />
      </div>
      {sub && <div className="mt-1.5 text-[11.5px] text-amber-700">{sub}</div>}
    </div>
  );
}
