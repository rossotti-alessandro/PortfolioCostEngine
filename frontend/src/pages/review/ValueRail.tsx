/** Side rail for the value being checked. The page stays the large region; this column only holds the decision. */

import { AskExpert, ExpertSuggestion } from "@/components/Expert";
import { SourceCrop } from "@/components/SourceCrop";
import { Badge, Button, Card, ErrorBox, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { cn } from "@/lib/format";
import { t, tm } from "@/lib/i18n";
import { whyYou } from "@/lib/trail";
import type { DocumentRow, Fact } from "@/lib/types";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Check, ChevronRight, History, Pencil, X } from "lucide-react";
import { useMemo, useState } from "react";
import { KIND_LABEL, QUEUE, type QueueKey, STATUS_TONE, displayValue } from "./shared";

export function ValueRail({
  all,
  ordered,
  loading,
  shownQueue,
  onQueue,
  active,
  activeId,
  onSelect,
  docId,
  isSheet,
  busy,
  error,
  onAccept,
  onCorrect,
  onReject,
  onUndo,
  doc,
  pid,
  onUseExpert,
}: {
  all: Fact[];
  ordered: Fact[];
  loading: boolean;
  shownQueue: QueueKey;
  onQueue: (key: QueueKey) => void;
  active: Fact | null;
  activeId: number | null;
  onSelect: (id: number) => void;
  docId: number | undefined;
  isSheet: boolean;
  busy: boolean;
  error: unknown;
  onAccept: () => void;
  onCorrect: () => void;
  onReject: () => void;
  onUndo: () => void;
  doc: DocumentRow | undefined;
  pid: number;
  onUseExpert: (value: string) => void;
}) {
  const [listOpen, setListOpen] = useState(true);
  const reviewed = all.filter((f) => f.status !== "extracted").length;
  const why = active ? whyYou(active) : [];
  const groups = useMemo(() => {
    const g = new Map<string, Fact[]>();
    for (const f of ordered) g.set(f.kind, [...(g.get(f.kind) ?? []), f]);
    return [...g.entries()];
  }, [ordered]);

  return (
    <Card data-review="rail" className="flex flex-col xl:h-full xl:min-h-0 xl:overflow-hidden">
      <div className="shrink-0 border-b border-line px-4 py-2.5">
        <div className="flex items-center justify-between gap-2">
          <span className="text-[13.5px] font-semibold text-navy-900">{t("Extracted values")}</span>
          <span className="num text-[12px] text-muted">
            {t("{done}/{total} reviewed", { done: reviewed, total: all.length })}
          </span>
        </div>
        <div className="mt-1.5 h-1 overflow-hidden rounded-[2px] bg-paper">
          <div
            className="h-full bg-teal-700 transition-all"
            style={{ width: `${all.length ? (reviewed / all.length) * 100 : 0}%` }}
          />
        </div>
        <div className="mt-1.5 text-[11px] text-subtle">
          <kbd className="rounded border border-line px-1">j</kbd>/
          <kbd className="rounded border border-line px-1">k</kbd> {t("move")} ·{" "}
          <kbd className="rounded border border-line px-1">a</kbd> {t("accept")} ·{" "}
          <kbd className="rounded border border-line px-1">e</kbd> {t("correct")} ·{" "}
          <kbd className="rounded border border-line px-1">r</kbd> {t("reject")}
        </div>
        {doc && <AskExpert doc={doc} pid={pid} open={all.filter(QUEUE[0].test).length} />}
        <div className="mt-2 flex flex-wrap gap-1" role="tablist" aria-label={t("Values to show")}>
          {QUEUE.map((q) => {
            const n = all.filter(q.test).length;
            return (
              <button
                key={q.key}
                type="button"
                role="tab"
                aria-selected={shownQueue === q.key}
                onClick={() => onQueue(q.key)}
                className={cn(
                  "rounded-[3px] px-2 py-0.5 text-[12px] font-medium ring-1 ring-inset",
                  shownQueue === q.key
                    ? "bg-navy-900 text-white ring-navy-900"
                    : q.key === "needs" && n > 0
                      ? "bg-amber-50 text-amber-700 ring-amber-700/25"
                      : "text-muted ring-line hover:text-ink",
                )}
              >
                {t(q.label)} · <span className="num">{n}</span>
              </button>
            );
          })}
        </div>
      </div>

      {active && (
        <div className="shrink-0 border-b border-line bg-paper/60 px-4 py-3">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <div className="text-[12px] text-subtle">
                {(active.fee_label && tm(active.fee_label)) ?? (KIND_LABEL[active.kind] && t(KIND_LABEL[active.kind]))}
              </div>
              <div className="truncate text-[13.5px] font-medium text-ink">{active.label}</div>
            </div>
            <Badge tone={STATUS_TONE[active.status]}>{t(active.status)}</Badge>
          </div>
          <div className="num mt-2 text-[22px] font-semibold text-navy-900">{displayValue(active)}</div>
          {why.length > 0 && (
            <div className="mt-1.5 flex items-start gap-1.5 text-[12px] text-amber-700">
              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              <span>{t("Why you: {reasons}", { reasons: why.join("; ") })}</span>
            </div>
          )}
          <ExpertSuggestion fact={active} onUse={onUseExpert} />
          {!isSheet && docId && active.evidence.page && active.evidence.bbox && (
            <div className="mt-2.5">
              <SourceCrop
                docId={docId}
                page={active.evidence.page}
                bbox={active.evidence.bbox}
                tag={displayValue(active)}
              />
            </div>
          )}
          {active.status === "corrected" && (
            <div className="mt-1.5 text-[12px] text-violet-700">
              {t("Extracted: {value} → corrected by reviewer (original kept)", {
                value: active.value_extracted ?? "–",
              })}
            </div>
          )}
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <Button onClick={onAccept} disabled={active.status === "accepted" || busy} title={t("Accept")}>
              <Check className="h-3.5 w-3.5" /> {t("Accept")}
            </Button>
            <Button size="sm" variant="outline" onClick={onCorrect} disabled={active.value === null || busy}>
              <Pencil className="h-3.5 w-3.5" /> {t("Correct")}
            </Button>
            <Button size="sm" variant="danger" onClick={onReject} disabled={busy}>
              <X className="h-3.5 w-3.5" /> {t("Reject")}
            </Button>
            {active.status !== "extracted" && (
              <Button size="sm" variant="ghost" onClick={onUndo} disabled={busy}>
                {t("Undo")}
              </Button>
            )}
          </div>
          {error ? <ErrorBox error={error} /> : null}
          <details className="group mt-2 text-[12px]">
            <summary className="flex cursor-pointer list-none items-center gap-1 text-muted [&::-webkit-details-marker]:hidden">
              <ChevronRight className="h-3.5 w-3.5 shrink-0 transition-transform group-open:rotate-90" />
              {t("Details of this value")}
            </summary>
            <dl className="mt-1.5 grid grid-cols-[90px_1fr] gap-x-2 gap-y-0.5">
              <dt className="text-subtle">{t("Source")}</dt>
              <dd className="text-muted">
                {active.evidence.page
                  ? t("page {page}, rectangle shown", { page: active.evidence.page })
                  : t("cell {ref}", { ref: `${active.evidence.sheet}!${active.evidence.cell}` })}
              </dd>
              <dt className="text-subtle">{t("Read by")}</dt>
              <dd className="text-muted">
                {active.evidence.engine} ·{" "}
                {t("confidence {pct}%", { pct: Math.round(active.evidence.confidence * 100) })}
              </dd>
              {active.isin && (
                <>
                  <dt className="text-subtle">ISIN</dt>
                  <dd className="font-mono text-muted">{active.isin}</dd>
                </>
              )}
              {active.measurement && (
                <>
                  <dt className="text-subtle">{t("Status")}</dt>
                  <dd className="text-muted">{active.measurement}</dd>
                </>
              )}
              <dt className="text-subtle">{t("Text")}</dt>
              <dd className="line-clamp-3 font-mono text-[11px] text-muted">{active.evidence.snippet}</dd>
            </dl>
            <FactHistory id={active.id} />
          </details>
        </div>
      )}

      <div className={cn("flex min-h-0 flex-col border-t border-line", listOpen && "xl:flex-1")}>
        <button
          type="button"
          aria-expanded={listOpen}
          onClick={() => setListOpen((open) => !open)}
          className="flex shrink-0 items-center gap-1 px-4 py-2 text-left text-[11px] font-semibold uppercase tracking-wide text-subtle"
        >
          <ChevronRight className={cn("h-3.5 w-3.5 shrink-0 transition-transform", listOpen && "rotate-90")} />
          {t("Value list")} · <span className="num">{ordered.length}</span>
        </button>
        {/* contain:paint keeps this long scroller from lengthening the page. */}
        {listOpen && (
          <div className="max-h-[50vh] overflow-auto [contain:paint] xl:max-h-full xl:min-h-0 xl:flex-1">
            {loading && <Spinner />}
            {!loading && !ordered.length && (
              <div className="px-4 py-6 text-center text-[12.5px] text-muted">
                {shownQueue === "needs" ? t("Nothing in this document needs you.") : t("No values here.")}
              </div>
            )}
            {groups.map(([kind, fs]) => (
              <div key={kind}>
                {/* Not sticky: a sticky label in this scroller lengthens the whole page. */}
                <div className="bg-surface px-4 pb-1 pt-2 text-[11px] font-semibold uppercase tracking-wide text-subtle">
                  {KIND_LABEL[kind] ? t(KIND_LABEL[kind]) : kind}
                </div>
                {fs.map((f) => (
                  <button
                    type="button"
                    key={f.id}
                    onClick={() => onSelect(f.id)}
                    className={cn(
                      "flex w-full items-center justify-between gap-3 border-l-2 px-4 py-1.5 text-left text-[12.5px] hover:bg-paper",
                      f.id === activeId ? "border-amber-700 bg-amber-50" : "border-transparent",
                    )}
                  >
                    <span className="min-w-[35%] flex-1">
                      <span className={cn("block truncate", f.status === "rejected" && "text-subtle line-through")}>
                        {f.label}
                      </span>
                      {f.fee_label && <span className="block truncate text-[11px] text-subtle">{tm(f.fee_label)}</span>}
                    </span>
                    <span className="flex min-w-0 max-w-[60%] items-center gap-2">
                      <span className="num truncate font-medium text-ink" title={displayValue(f)}>
                        {displayValue(f)}
                      </span>
                      <span className="sr-only">{t(f.status)}</span>
                      <span
                        className={cn(
                          "h-2 w-2 shrink-0 rounded-full",
                          f.status === "accepted"
                            ? "bg-teal-700"
                            : f.status === "corrected"
                              ? "bg-violet-700"
                              : f.status === "rejected"
                                ? "bg-red-700"
                                : "bg-line-strong",
                        )}
                        title={t(f.status)}
                      />
                    </span>
                  </button>
                ))}
              </div>
            ))}
          </div>
        )}
      </div>
    </Card>
  );
}

function FactHistory({ id }: { id: number }) {
  const { data } = useQuery({ queryKey: ["history", id], queryFn: () => api.history(id) });
  if (!data?.length) return null;
  return (
    <details className="mt-2">
      <summary className="flex cursor-pointer items-center gap-1 text-muted">
        <History className="h-3 w-3" />{" "}
        {data.length > 1 ? t("{n} review events", { n: data.length }) : t("{n} review event", { n: data.length })}
      </summary>
      <ul className="mt-1 space-y-1">
        {data.map((h, i) => (
          <li key={i} className="text-muted">
            <span className="num text-subtle">{h.at.slice(0, 16).replace("T", " ")}</span> · {h.user} · {h.action}
            {h.old !== h.new && ` ${h.old ?? "–"} → ${h.new ?? "–"}`}
            {h.reason && <span className="italic"> “{h.reason}”</span>}
          </li>
        ))}
      </ul>
    </details>
  );
}
