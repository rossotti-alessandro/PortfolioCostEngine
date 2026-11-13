import { PdfEvidence, SheetEvidence } from "@/components/EvidenceViewer";
import { SourceCrop } from "@/components/SourceCrop";
import { Badge, Button, Card, Dialog, ErrorBox, Field, Spinner, inputCls } from "@/components/ui";
import { api } from "@/lib/api";
import { DOC_TYPES, cn, num } from "@/lib/format";
import { t, tm } from "@/lib/i18n";
import { whyYou } from "@/lib/trail";
import type { Fact } from "@/lib/types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Check, FileSpreadsheet, FileText, History, Pencil, ScanLine, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";

const KIND_LABEL: Record<string, string> = {
  position: "Positions",
  doc_total: "Totals",
  fee_observed: "Fees charged",
  cash_debit: "Fee debits",
  fee_rule: "Contract terms",
  product_cost: "Product costs",
  reported: "Reported by bank",
  meta: "Document details",
};
const STATUS_TONE: Record<string, string> = {
  extracted: "grey",
  accepted: "teal",
  corrected: "violet",
  rejected: "red",
  manual: "navy",
};

/** The queue: what needs a person first, what the checks confirmed, what a person already handled. */
const QUEUE = [
  { key: "needs", label: "Needs you", test: (f: Fact) => whyYou(f).length > 0 },
  { key: "auto", label: "Confirmed by checks", test: (f: Fact) => f.status === "extracted" && !whyYou(f).length },
  { key: "person", label: "Checked by a person", test: (f: Fact) => f.status !== "extracted" },
  { key: "all", label: "All", test: () => true },
] as const;
type QueueKey = (typeof QUEUE)[number]["key"];

function displayValue(f: Fact) {
  if (f.value === null) return f.measurement === "unknown" ? t("not disclosed") : String(f.extra?.entity ?? "") || "–";
  if (f.field === "rate_pct") return `${f.value}%`;
  return `${f.currency ? `${f.currency} ` : ""}${num(f.value, 2)}`;
}

export default function ReviewPage() {
  const pid = Number(useParams().id);
  const [sp, setSp] = useSearchParams();
  const docs = useQuery({ queryKey: ["documents", pid], queryFn: () => api.documents(pid) });
  const docId = Number(sp.get("doc")) || docs.data?.[0]?.id;
  const doc = docs.data?.find((d) => d.id === docId);
  const facts = useQuery({ queryKey: ["facts", docId], queryFn: () => api.facts(docId!), enabled: !!docId });
  const [activeId, setActiveId] = useState<number | null>(Number(sp.get("fact")) || null);
  const active = facts.data?.find((f) => f.id === activeId) ?? null;
  const [editing, setEditing] = useState<"correct" | "reject" | null>(null);
  const [queue, setQueue] = useState<QueueKey | null>(null);
  const qc = useQueryClient();
  // Open on what needs a person; a document with nothing flagged opens on all its values.
  const shownQueue: QueueKey = queue ?? (facts.data?.some(QUEUE[0].test) ? "needs" : "all");

  const review = useMutation({
    mutationFn: (b: { id: number; action: string; value?: string; reason?: string }) => api.review(b.id, b),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["facts", docId] });
      qc.invalidateQueries({ queryKey: ["analysis", pid] });
      qc.invalidateQueries({ queryKey: ["history"] });
      setEditing(null);
    },
  });

  const ordered = useMemo(
    () => (facts.data ?? []).filter(QUEUE.find((q) => q.key === shownQueue)!.test),
    [facts.data, shownQueue],
  );
  useEffect(() => {
    if (ordered.length && !ordered.some((f) => f.id === activeId)) setActiveId(ordered[0].id);
  }, [ordered, activeId]);
  // A value picked on the page may sit outside the current queue: show all values rather than jump away.
  const select = (f: Fact) => {
    if (!ordered.some((x) => x.id === f.id)) setQueue("all");
    setActiveId(f.id);
  };
  const move = useCallback(
    (d: number) => {
      if (!ordered.length) return;
      const i = ordered.findIndex((f) => f.id === activeId);
      const n = ordered[Math.max(0, Math.min(ordered.length - 1, i + d))];
      setActiveId(n.id);
    },
    [ordered, activeId],
  );
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if (editing || (e.target as HTMLElement).closest("input,textarea,select")) return;
      if (e.key === "j" || e.key === "ArrowDown") {
        e.preventDefault();
        move(1);
      } else if (e.key === "k" || e.key === "ArrowUp") {
        e.preventDefault();
        move(-1);
      } else if (e.key === "a" && active) {
        review.mutate({ id: active.id, action: "accept" });
        move(1);
      } else if (e.key === "e" && active) setEditing("correct");
      else if (e.key === "r" && active) setEditing("reject");
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [move, active, editing, review]);

  const groups = useMemo(() => {
    const g = new Map<string, Fact[]>();
    for (const f of ordered) g.set(f.kind, [...(g.get(f.kind) ?? []), f]);
    return [...g.entries()];
  }, [ordered]);

  if (docs.isLoading) return <Spinner />;
  if (!docs.data?.length) return <Card className="p-8 text-center text-muted">{t("Upload documents first.")}</Card>;
  const isSheet = doc?.filename.toLowerCase().endsWith(".xlsx");
  const all = facts.data ?? [];
  const reviewed = all.filter((f) => f.status !== "extracted").length;
  const why = active ? whyYou(active) : [];

  return (
    <div className="grid h-[calc(100vh-205px)] min-h-[560px] gap-3 lg:grid-cols-[230px_minmax(0,1fr)_400px]">
      <Card className="hidden min-h-0 flex-col overflow-hidden lg:flex">
        <div className="border-b border-line px-3 py-2 text-[12px] font-medium uppercase tracking-wide text-subtle">
          {t("Documents")}
        </div>
        <ul className="min-h-0 flex-1 overflow-auto py-1">
          {docs.data.map((d) => (
            <li key={d.id}>
              <button
                type="button"
                onClick={() => {
                  setSp({ doc: String(d.id) });
                  setActiveId(null);
                }}
                className={cn(
                  "flex w-full items-start gap-2 px-3 py-2 text-left text-[12.5px] hover:bg-paper",
                  d.id === docId && "bg-navy-100/70 text-navy-900",
                )}
              >
                {d.filename.endsWith(".xlsx") ? (
                  <FileSpreadsheet className="mt-0.5 h-3.5 w-3.5 shrink-0 text-teal-700" />
                ) : (
                  <FileText className="mt-0.5 h-3.5 w-3.5 shrink-0 text-navy-700" />
                )}
                <span className="min-w-0">
                  <span className="block truncate font-medium">{t(DOC_TYPES[d.doc_type])}</span>
                  <span className="block truncate text-[11.5px] text-subtle">{d.filename}</span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      </Card>

      <Card className="flex min-h-0 flex-col overflow-hidden">
        <div className="flex items-center justify-between gap-2 border-b border-line px-4 py-2">
          <div className="min-w-0">
            <div className="truncate text-[13.5px] font-semibold text-navy-900">{doc?.filename}</div>
            <div className="text-[11.5px] text-subtle">
              {doc?.profile.institution} · {t(DOC_TYPES[doc?.doc_type ?? "unknown"])} · sha256{" "}
              {doc?.sha256.slice(0, 10)}…
            </div>
          </div>
          {doc?.profile.engines.includes("tesseract-ocr") && (
            <Badge tone="violet">
              <ScanLine className="h-3 w-3" /> {t("Scanned · OCR")}
            </Badge>
          )}
        </div>
        <div className="min-h-0 flex-1">
          {docId &&
            facts.data &&
            (isSheet ? (
              <SheetEvidence docId={docId} facts={facts.data} activeId={activeId} onSelect={select} />
            ) : (
              <PdfEvidence
                docId={docId}
                facts={facts.data}
                activeId={activeId}
                page={active?.evidence.page ?? undefined}
                onSelect={select}
              />
            ))}
        </div>
      </Card>

      <Card className="flex min-h-0 flex-col overflow-hidden">
        <div className="border-b border-line px-4 py-2.5">
          <div className="flex items-center justify-between">
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
          <div className="mt-2 flex flex-wrap gap-1" role="tablist" aria-label={t("Values to show")}>
            {QUEUE.map((q) => {
              const n = all.filter(q.test).length;
              return (
                <button
                  key={q.key}
                  type="button"
                  role="tab"
                  aria-selected={shownQueue === q.key}
                  onClick={() => setQueue(q.key)}
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
          <div className="border-b border-line bg-paper/60 px-4 py-3">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <div className="text-[12px] text-subtle">
                  {(active.fee_label && tm(active.fee_label)) ??
                    (KIND_LABEL[active.kind] && t(KIND_LABEL[active.kind]))}
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
              <div className="text-[12px] text-violet-700">
                {t("Extracted: {value} → corrected by reviewer (original kept)", {
                  value: active.value_extracted ?? "–",
                })}
              </div>
            )}
            <dl className="mt-2 grid grid-cols-[90px_1fr] gap-x-2 gap-y-0.5 text-[12px]">
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
              <dd className="line-clamp-2 font-mono text-[11px] text-muted">{active.evidence.snippet}</dd>
            </dl>
            <div className="mt-3 flex flex-wrap gap-2">
              <Button
                size="sm"
                onClick={() => review.mutate({ id: active.id, action: "accept" })}
                disabled={active.status === "accepted"}
              >
                <Check className="h-3.5 w-3.5" /> {t("Accept")}
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => setEditing("correct")}
                disabled={active.value === null}
              >
                <Pencil className="h-3.5 w-3.5" /> {t("Correct")}
              </Button>
              <Button size="sm" variant="danger" onClick={() => setEditing("reject")}>
                <X className="h-3.5 w-3.5" /> {t("Reject")}
              </Button>
              {active.status !== "extracted" && (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => review.mutate({ id: active.id, action: "reset", reason: "reset" })}
                >
                  {t("Undo")}
                </Button>
              )}
            </div>
            {review.error && <ErrorBox error={review.error} />}
            <FactHistory id={active.id} />
          </div>
        )}
        <div className="min-h-0 flex-1 overflow-auto">
          {facts.isLoading && <Spinner />}
          {!facts.isLoading && !ordered.length && (
            <div className="px-4 py-6 text-center text-[12.5px] text-muted">
              {shownQueue === "needs" ? t("Nothing in this document needs you.") : t("No values here.")}
            </div>
          )}
          {groups.map(([kind, fs]) => (
            <div key={kind}>
              <div className="sticky top-0 z-10 bg-surface/95 px-4 pb-1 pt-3 text-[11px] font-semibold uppercase tracking-wide text-subtle backdrop-blur">
                {KIND_LABEL[kind] ? t(KIND_LABEL[kind]) : kind}
              </div>
              {fs.map((f) => (
                <button
                  type="button"
                  key={f.id}
                  onClick={() => setActiveId(f.id)}
                  className={cn(
                    "flex w-full items-center justify-between gap-3 border-l-2 px-4 py-1.5 text-left text-[12.5px] hover:bg-paper",
                    f.id === activeId ? "border-[#d99a00] bg-amber-50" : "border-transparent",
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
      </Card>
      {active && (
        <EditDialog
          mode={editing}
          fact={active}
          busy={review.isPending}
          onClose={() => setEditing(null)}
          onSubmit={(value, reason) => review.mutate({ id: active.id, action: editing!, value, reason })}
        />
      )}
    </div>
  );
}

function FactHistory({ id }: { id: number }) {
  const { data } = useQuery({ queryKey: ["history", id], queryFn: () => api.history(id) });
  if (!data?.length) return null;
  return (
    <details className="mt-2 text-[12px]">
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

function EditDialog({
  mode,
  fact,
  busy,
  onClose,
  onSubmit,
}: {
  mode: "correct" | "reject" | null;
  fact: Fact;
  busy: boolean;
  onClose: () => void;
  onSubmit: (value: string | undefined, reason: string) => void;
}) {
  const [value, setValue] = useState(fact.value ?? "");
  const [reason, setReason] = useState("");
  // biome-ignore lint/correctness/useExhaustiveDependencies: reset the form whenever the dialog opens for another action
  useEffect(() => {
    setValue(fact.value ?? "");
    setReason("");
  }, [fact, mode]);
  return (
    <Dialog
      open={!!mode}
      onOpenChange={(o) => !o && onClose()}
      title={mode === "reject" ? t("Reject this value") : t("Correct this value")}
      description={t("The original extraction is kept. Your change is recorded with your name, time and reason.")}
    >
      <form
        className="space-y-3"
        onSubmit={(e) => {
          e.preventDefault();
          onSubmit(mode === "correct" ? value : undefined, reason);
        }}
      >
        <div className="rounded-[var(--radius-control)] bg-paper px-3 py-2 text-[12.5px]">
          <div className="text-subtle">{fact.label}</div>
          <div className="num font-medium">{t("Extracted: {value}", { value: fact.value_extracted ?? "–" })}</div>
        </div>
        {mode === "correct" && (
          <Field label={t("Correct value")} hint={t("Number only, e.g. 1340.00")}>
            <input
              // biome-ignore lint/a11y/noAutofocus: the dialog exists to type this one value
              autoFocus
              className={inputCls}
              value={value}
              onChange={(e) => setValue(e.target.value)}
              inputMode="decimal"
              required
            />
          </Field>
        )}
        <Field label={t("Reason")} hint={t("Required. Cite the document you checked.")}>
          <textarea
            className={cn(inputCls, "h-20 py-2")}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            required
          />
        </Field>
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>
            {t("Cancel")}
          </Button>
          <Button type="submit" variant={mode === "reject" ? "danger" : "primary"} loading={busy}>
            {mode === "reject" ? t("Reject value") : t("Save correction")}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
