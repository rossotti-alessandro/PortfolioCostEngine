import { Button, Card, CardHeader, Empty, ErrorBox, Field, Kpi, Spinner, inputCls } from "@/components/ui";
import { chf, cn } from "@/lib/format";
import { t } from "@/lib/i18n";
import { useQuery } from "@tanstack/react-query";
import { ArrowDown, BarChart3, Info } from "lucide-react";
import { useState } from "react";
import { type Funnel, crm, ratioPct } from "./api";
import { CrmHeader, NewContactButton, useMeta } from "./common";

const th = "px-3 py-2.5 font-medium";
const thr = `${th} text-right`;

/** Funnel bars: width is the API's share_of_total; the step conversion sits between bars. */
function FunnelBars({ f }: { f: Funnel }) {
  return (
    <ol className="space-y-1 px-5 py-5" aria-label={t("Conversion funnel chart")}>
      {f.stages.map((s, i) => (
        <li key={s.stage}>
          {i > 0 && (
            <div className="flex items-center justify-center gap-2 py-1 text-[12px] text-muted">
              <ArrowDown className="h-3.5 w-3.5" aria-hidden />
              <span className="num font-medium text-ink">{ratioPct(s.conversion_from_previous)}</span>
              <span>{t("continue")}</span>
              {!!s.drop_off && <span className="num text-red-700">· {t("{n} dropped", { n: s.drop_off })}</span>}
            </div>
          )}
          <div className="flex items-center gap-3">
            <div className="w-36 shrink-0 text-right text-[13px] font-medium text-ink">{t(s.label)}</div>
            <div className="relative h-9 flex-1">
              <div
                data-testid={`bar-${s.stage}`}
                className={cn(
                  "mx-auto flex h-full min-w-[2.5rem] items-center justify-center rounded-md text-[13px] font-semibold text-white",
                  s.stage === "won" ? "bg-teal-700" : "bg-navy-900",
                )}
                style={{
                  width: `${Number(s.share_of_total ?? 0) * 100}%`,
                  opacity: s.stage === "won" ? 1 : 1 - i * 0.12,
                }}
              >
                <span className="num">{s.reached}</span>
              </div>
            </div>
            <div className="num w-16 shrink-0 text-[12px] text-subtle">{ratioPct(s.share_of_total, 0)}</div>
          </div>
        </li>
      ))}
    </ol>
  );
}

export default function FunnelPage() {
  const { data: meta } = useMeta();
  const [filters, setFilters] = useState({ since: "", until: "", owner: "", source: "" });
  const [details, setDetails] = useState(false);
  const q = Object.fromEntries(Object.entries(filters).map(([k, v]) => [k, v || undefined]));
  const { data: f, isLoading, error } = useQuery({ queryKey: ["crm", "funnel", q], queryFn: () => crm.funnel(q) });
  const set = (k: keyof typeof filters) => (e: { target: { value: string } }) =>
    setFilters({ ...filters, [k]: e.target.value });
  const stageLabel = (id: string) => meta?.stages.find((s) => s.id === id)?.label ?? id;

  return (
    <div>
      <CrmHeader synthetic={f?.synthetic} actions={<NewContactButton />} />
      <div className="mx-auto max-w-[1440px] space-y-5 px-4 py-6 sm:px-8">
        <Card className="grid gap-3 p-4 sm:grid-cols-2 lg:grid-cols-4">
          <Field label={t("Created from")}>
            <input type="date" className={inputCls} value={filters.since} onChange={set("since")} />
          </Field>
          <Field label={t("Created until")}>
            <input type="date" className={inputCls} value={filters.until} onChange={set("until")} />
          </Field>
          <Field label={t("Owner")}>
            <select className={inputCls} value={filters.owner} onChange={set("owner")}>
              <option value="">{t("Everyone")}</option>
              {f?.owners.map((o) => (
                <option key={o}>{o}</option>
              ))}
            </select>
          </Field>
          <Field label={t("Source")}>
            <select className={inputCls} value={filters.source} onChange={set("source")}>
              <option value="">{t("All sources")}</option>
              {meta?.sources.map((s) => (
                <option key={s.id} value={s.id}>
                  {t(s.label)}
                </option>
              ))}
            </select>
          </Field>
        </Card>

        {isLoading ? (
          <Spinner />
        ) : error ? (
          <ErrorBox error={error} />
        ) : !f || f.total === 0 ? (
          <Card>
            <Empty icon={<BarChart3 className="h-8 w-8" />} title={t("No contacts in this cohort")}>
              {t("Change the filters, add contacts, or load the synthetic CRM from the board.")}
            </Empty>
          </Card>
        ) : (
          <>
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
              <Kpi
                label={t("Contacts in cohort")}
                value={f.total}
                sub={t("{open} open · {won} won · {lost} lost", { open: f.open, won: f.won, lost: f.lost })}
              />
              <Kpi
                label={t("Lead to client")}
                value={ratioPct(f.overall_conversion)}
                tone="teal"
                sub={t("Won ÷ all contacts in the cohort")}
              />
              <Kpi label={t("Win rate")} value={ratioPct(f.win_rate)} sub={t("Won ÷ (won + lost), closed only")} />
              <Kpi
                label={t("Median time to win")}
                value={f.median_days_to_win ? t("{n} days", { n: f.median_days_to_win }) : t("Not determined")}
                sub={t("From first contact to won")}
              />
            </div>

            <div className="flex justify-end">
              <Button variant="ghost" size="sm" aria-expanded={details} onClick={() => setDetails(!details)}>
                <Info className="h-4 w-4" /> {details ? t("Hide details") : t("Show details")}
              </Button>
            </div>
            <div className={cn("grid gap-5", details && "xl:grid-cols-[1fr_1fr]")}>
              <Card>
                <CardHeader
                  title={t("Conversion funnel")}
                  subtitle={t(
                    "Contacts that reached each stage at least once. Lost contacts count up to where they dropped out.",
                  )}
                />
                <FunnelBars f={f} />
              </Card>
              {details && (
                <Card>
                  <CardHeader
                    title={t("By stage")}
                    subtitle={t("Table twin of the chart, with time spent and open assets.")}
                  />
                  <div className="overflow-x-auto">
                    <table className="w-full text-[13px]" aria-label={t("Funnel by stage")}>
                      <thead>
                        <tr className="border-b border-line text-left text-[11.5px] uppercase tracking-wide text-subtle">
                          <th className={`${th} pl-5`}>{t("Stage")}</th>
                          <th className={thr}>{t("Reached")}</th>
                          <th className={thr}>{t("Step conversion")}</th>
                          <th className={thr}>{t("Now in stage")}</th>
                          <th className={thr}>{t("Median days")}</th>
                          <th className={`${thr} pr-5`}>{t("Open assets")}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {f.stages.map((s) => (
                          <tr key={s.stage} className="border-b border-line last:border-0" data-stage={s.stage}>
                            <td className="px-3 py-2.5 pl-5 font-medium text-ink">{t(s.label)}</td>
                            <td className="num px-3 py-2.5 text-right">{s.reached}</td>
                            <td className="num px-3 py-2.5 text-right">
                              {s.conversion_from_previous === null && s.stage === "lead"
                                ? "–"
                                : ratioPct(s.conversion_from_previous)}
                            </td>
                            <td className="num px-3 py-2.5 text-right">{s.current}</td>
                            <td className="num px-3 py-2.5 text-right">{s.median_days_in_stage ?? "–"}</td>
                            <td className="num whitespace-nowrap px-3 py-2.5 pr-5 text-right">
                              {s.stage === "won" ? "–" : chf(s.aum.CHF ?? "0")}
                              {s.aum_unknown > 0 && (
                                <div className="text-[11.5px] text-subtle">
                                  +{t("{n} not estimated", { n: s.aum_unknown })}
                                </div>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Card>
              )}
            </div>

            {details && (
              <div className="grid gap-5 xl:grid-cols-2">
                <Card>
                  <CardHeader
                    title={t("Why prospects are lost")}
                    subtitle={t("Reason and the furthest stage they reached.")}
                  />
                  {f.lost_reasons.length === 0 ? (
                    <Empty title={t("No lost contacts in this cohort")} />
                  ) : (
                    <table className="w-full text-[13px]" aria-label={t("Lost reasons")}>
                      <thead>
                        <tr className="border-b border-line text-left text-[11.5px] uppercase tracking-wide text-subtle">
                          <th className={`${th} pl-5`}>{t("Reason")}</th>
                          <th className={thr}>{t("Lost")}</th>
                          <th className={`${th} pr-5`}>{t("Lost after")}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {f.lost_reasons.map((r) => (
                          <tr key={r.reason} className="border-b border-line last:border-0">
                            <td className="px-3 py-2.5 pl-5 text-ink">{t(r.label)}</td>
                            <td className="num px-3 py-2.5 text-right">{r.count}</td>
                            <td className="px-3 py-2.5 pr-5 text-[12.5px] text-muted">
                              {Object.entries(r.lost_after)
                                .map(([s, n]) => `${t(stageLabel(s))} ${n}`)
                                .join(" · ")}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </Card>
                <Card>
                  <CardHeader
                    title={t("By source")}
                    subtitle={t("Where contacts come from and how well each source converts.")}
                  />
                  <table className="w-full text-[13px]" aria-label={t("Conversion by source")}>
                    <thead>
                      <tr className="border-b border-line text-left text-[11.5px] uppercase tracking-wide text-subtle">
                        <th className={`${th} pl-5`}>{t("Source")}</th>
                        <th className={thr}>{t("Contacts")}</th>
                        <th className={thr}>{t("Open")}</th>
                        <th className={thr}>{t("Won")}</th>
                        <th className={thr}>{t("Lost")}</th>
                        <th className={`${thr} pr-5`}>{t("Win rate")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {f.by_source.map((s) => (
                        <tr key={s.source} className="border-b border-line last:border-0">
                          <td className="px-3 py-2.5 pl-5 text-ink">{t(s.label)}</td>
                          <td className="num px-3 py-2.5 text-right">{s.contacts}</td>
                          <td className="num px-3 py-2.5 text-right">{s.open}</td>
                          <td className="num px-3 py-2.5 text-right">{s.won}</td>
                          <td className="num px-3 py-2.5 text-right">{s.lost}</td>
                          <td className="num whitespace-nowrap px-3 py-2.5 pr-5 text-right">{ratioPct(s.win_rate)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </Card>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
