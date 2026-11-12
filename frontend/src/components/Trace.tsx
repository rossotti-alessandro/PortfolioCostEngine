import { api } from "@/lib/api";
import { LAYER, MEASUREMENT, chf, cn } from "@/lib/format";
import { t } from "@/lib/i18n";
import type { Atom, EvidenceRef, Ledger } from "@/lib/types";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { useQuery } from "@tanstack/react-query";
import { ChevronRight, ExternalLink, Maximize2, Minimize2, X } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { DecisionTrail } from "./DecisionTrail";
import { PdfEvidence, SheetEvidence } from "./EvidenceViewer";
import { SourceCrop } from "./SourceCrop";
import { Badge, Button, Fold, Spinner, StatusBadge } from "./ui";

/** What a click on a number opens. The amounts shown are always the API's; the frontend only selects lines. */
export type TraceTarget =
  | { kind: "sum"; title: string; amount: string; ledger: Ledger; pick: (a: Atom) => boolean }
  | { kind: "diff"; title: string; amount: string; prefix?: string; left: SumTarget; right: SumTarget }
  | { kind: "atom"; atom: Atom; ledger: Ledger }
  | { kind: "source"; title: string; evidence: EvidenceRef[] };
type SumTarget = Extract<TraceTarget, { kind: "sum" }>;

/** A total and the ledger lines it is made of. */
export const sumOf = (
  title: string,
  amount: string,
  ledger: Ledger,
  pick: (a: Atom) => boolean = () => true,
): SumTarget => ({ kind: "sum", title, amount, ledger, pick });

function fmtValue(x: EvidenceRef): string {
  if (x.value === null) return t("no value");
  if (x.field === "rate_pct") return `${x.value}%`;
  return x.currency ? chf(x.value, 2, `${x.currency} `) : x.value;
}

/** Result → computation → line → source page, with a breadcrumb back up.
 *  A side panel, not a modal: the page stays usable and clicking another number replaces the content. */
export function TraceDialog({ root, onClose }: { root: TraceTarget | null; onClose: () => void }) {
  return root ? <TraceStack key={titleOf(root)} root={root} onClose={onClose} /> : null;
}

function titleOf(x: TraceTarget): string {
  return x.kind === "atom" ? x.atom.label : x.title;
}

function TraceStack({ root, onClose }: { root: TraceTarget; onClose: () => void }) {
  const [stack, setStack] = useState<TraceTarget[]>([root]);
  const top = stack[stack.length - 1];
  const push = (x: TraceTarget) => setStack([...stack, x]);
  useEffect(() => {
    // Leave room for the panel on wide screens so it does not cover the numbers (index.css).
    document.body.dataset.evidence = "open";
    return () => {
      delete document.body.dataset.evidence;
    };
  }, []);
  return (
    <DialogPrimitive.Root open modal={false} onOpenChange={(o) => !o && onClose()}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Content
          aria-describedby={undefined}
          onInteractOutside={(e) => e.preventDefault()}
          onOpenAutoFocus={(e) => e.preventDefault()}
          className="no-print fixed inset-y-0 right-0 z-50 flex w-full max-w-[600px] flex-col border-l border-line bg-surface shadow-[-8px_0_24px_rgb(11_37_69/0.08)]"
        >
          <div className="flex items-start justify-between gap-3 border-b border-line px-5 py-4">
            <div className="min-w-0">
              <div className="text-[11.5px] font-semibold uppercase tracking-wider text-subtle">{t("Evidence")}</div>
              <DialogPrimitive.Title className="mt-0.5 text-base font-semibold text-navy-900">
                {titleOf(top)}
              </DialogPrimitive.Title>
              <p className="mt-0.5 text-[13px] text-muted">{describe(top)}</p>
            </div>
            <DialogPrimitive.Close className="rounded p-1 text-muted hover:bg-paper" aria-label={t("Close")}>
              <X className="h-4 w-4" />
            </DialogPrimitive.Close>
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">
            {stack.length > 1 && (
              <nav
                aria-label={t("Where this number comes from")}
                className="-mt-1 mb-3 flex flex-wrap items-center gap-1 text-[12.5px]"
              >
                {stack.map((x, i) => (
                  <span key={`${titleOf(x)}-${i}`} className="flex items-center gap-1">
                    {i > 0 && <ChevronRight className="h-3.5 w-3.5 text-subtle" />}
                    {i < stack.length - 1 ? (
                      <button
                        type="button"
                        className="text-teal-700 hover:underline"
                        onClick={() => setStack(stack.slice(0, i + 1))}
                      >
                        {titleOf(x)}
                      </button>
                    ) : (
                      <span className="text-muted">{titleOf(x)}</span>
                    )}
                  </span>
                ))}
              </nav>
            )}
            {top.kind === "sum" && <SumView x={top} onPick={push} />}
            {top.kind === "diff" && <DiffView x={top} onPick={push} />}
            {top.kind === "atom" && <AtomView atom={top.atom} ledger={top.ledger} onPick={push} />}
            {top.kind === "source" && <SourcePane evidence={top.evidence} />}
          </div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}

function describe(x: TraceTarget): string {
  if (x.kind === "atom")
    return `${x.atom.fee_label} · ${LAYER[x.atom.layer] ? t(LAYER[x.atom.layer].name) : x.atom.layer}`;
  if (x.kind === "sum") return t("How this number is calculated");
  if (x.kind === "diff") return t("Difference between the two totals");
  return t("Where this was read");
}

/* ------------------------------------------------------------------ computation of a total */

function SumView({ x, onPick }: { x: SumTarget; onPick: (t: TraceTarget) => void }) {
  const lines = x.ledger.atoms.filter(x.pick);
  const counted = lines.filter((a) => a.role === "counted").sort((a, b) => Number(b.amount) - Number(a.amount));
  const unknown = lines.filter((a) => a.role === "unknown");
  const shown = lines.filter((a) => !["counted", "unknown", "not_applicable"].includes(a.role ?? ""));
  const total = Number(x.amount) || 1;
  const row = (a: Atom, muted = false) => (
    <tr
      key={a.id}
      tabIndex={0}
      onClick={() => onPick({ kind: "atom", atom: a, ledger: x.ledger })}
      onKeyDown={(e) => e.key === "Enter" && onPick({ kind: "atom", atom: a, ledger: x.ledger })}
      className="cursor-pointer border-t border-line/70 hover:bg-teal-50 focus:bg-teal-50 focus:outline-none"
    >
      <td className="py-2 pr-3">
        <div className={cn("font-medium", muted ? "text-subtle" : "text-ink")}>{a.label}</div>
        <div className="text-[12px] text-muted">
          {a.fee_label}
          {a.institution && ` · ${a.institution}`}
        </div>
      </td>
      <td className="px-2 py-2">
        <StatusBadge m={a.measurement} />
      </td>
      <td className="w-24 px-2 py-2">
        {a.role === "counted" && (
          <div className="h-1.5 rounded-full bg-paper" aria-hidden>
            <div className="h-1.5 rounded-full bg-teal-700" style={{ width: `${(Number(a.amount) / total) * 100}%` }} />
          </div>
        )}
      </td>
      <td className="num py-2 pl-2 text-right">
        {a.amount === null ? (
          <span className="font-medium text-red-700">{t("Not determined")}</span>
        ) : muted ? (
          <s>{chf(a.amount, 2)}</s>
        ) : (
          chf(a.amount, 2)
        )}
      </td>
    </tr>
  );
  return (
    <div className="space-y-3 text-[13px]">
      <div>
        <div className="num text-2xl font-semibold text-navy-900">{chf(x.amount, 2)}</div>
        <p className="mt-1 text-muted">
          {t("Sum of {n} counted lines. Click a line to see its calculation and the page it was read from.", {
            n: counted.length,
          })}
          {unknown.length > 0 &&
            ` ${t("{n} more are not determined and are not counted as zero: the real figure is at least this.", { n: unknown.length })}`}
        </p>
      </div>
      <table className="w-full">
        <tbody>
          {counted.map((a) => row(a))}
          {unknown.map((a) => row(a))}
        </tbody>
      </table>
      {shown.length > 0 && (
        <Fold title={t("Shown, not added")} summary={t("{n} linked or non-paid lines", { n: shown.length })}>
          <table className="w-full">
            <tbody>{shown.map((a) => row(a, true))}</tbody>
          </table>
        </Fold>
      )}
    </div>
  );
}

function DiffView({ x, onPick }: { x: Extract<TraceTarget, { kind: "diff" }>; onPick: (t: TraceTarget) => void }) {
  const item = (s: SumTarget, sign: string) => (
    <button
      type="button"
      onClick={() => onPick(s)}
      className="flex w-full items-center justify-between rounded-md border border-line px-4 py-3 text-left hover:bg-teal-50"
    >
      <span>
        <span className="mr-2 font-mono text-subtle">{sign}</span>
        {s.title}
      </span>
      <span className="num font-medium">{chf(s.amount, 2)}</span>
    </button>
  );
  return (
    <div className="space-y-2 text-[13px]">
      {item(x.left, " ")}
      {item(x.right, "−")}
      <div className="flex items-center justify-between border-t-2 border-navy-900/20 px-4 pt-3 font-semibold">
        <span>= {x.title}</span>
        <span className="num text-teal-700">
          {x.prefix && <span className="mr-1 text-[12px] font-normal">{x.prefix}</span>}
          {chf(x.amount, 2)}
        </span>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ one line: formula + inputs + page */

const ROLE_LABEL: Record<EvidenceRef["role"], string> = {
  value: "Read from the document",
  basis: "Holding value used as basis",
  fx_rate: "Exchange rate",
};

function AtomView({ atom, ledger, onPick }: { atom: Atom; ledger: Ledger; onPick: (t: TraceTarget) => void }) {
  const related = ledger.atoms.filter((a) => a.included_in === atom.id || a.corroborates === atom.id);
  const parent = ledger.atoms.find((a) => a.id === (atom.included_in ?? atom.corroborates));
  const go = (a: Atom) => onPick({ kind: "atom", atom: a, ledger });
  const usedIn =
    atom.role === "counted"
      ? [
          `${LAYER[atom.layer] ? t(LAYER[atom.layer].name) : atom.layer} ${chf(ledger.by_layer[atom.layer], 0)}`,
          `${t("Known annual cost")} ${chf(ledger.total_known, 0)}`,
        ]
      : parent
        ? [t("Part of: {label}", { label: parent.label })]
        : [t("Shown, not added to the total")];
  return (
    <div className="space-y-5">
      <div className="space-y-3 text-[13px]">
        <div>
          <div className="text-[12px] text-subtle">{t("Annual amount")}</div>
          <div className="num text-2xl font-semibold text-navy-900">
            {atom.amount === null ? t("Not determined") : chf(atom.amount, 2)}
          </div>
          {atom.bps && <div className="num text-muted">{t("{bps} bps of assets reviewed", { bps: atom.bps })}</div>}
        </div>
        <div className="flex flex-wrap gap-1.5">
          <StatusBadge m={atom.measurement} />
          <Badge>
            {atom.incidence === "embedded"
              ? t("Inside product price (NAV)")
              : atom.incidence === "tax"
                ? t("Tax")
                : t("Debited from account")}
          </Badge>
          {atom.role === "included_in_parent" && <Badge tone="violet">{t("Included in parent · not added")}</Badge>}
          {atom.role === "corroborating" && <Badge tone="violet">{t("Second evidence · counted once")}</Badge>}
          {atom.role === "not_a_paid_cost" && <Badge>{t("Not a paid cost · not counted")}</Badge>}
        </div>
        <p className="text-[12.5px] text-muted">
          {MEASUREMENT[atom.measurement] && t(MEASUREMENT[atom.measurement].help)}
        </p>
        {atom.formula && (
          <div>
            <div className="text-[12px] text-subtle">{t("Calculation")}</div>
            <div className="num mt-0.5 rounded-md bg-paper px-3 py-2 font-mono text-[12px] text-ink">
              {atom.formula}
            </div>
          </div>
        )}
        {atom.note && <p className="rounded-md bg-amber-50 px-3 py-2 text-[12.5px] text-amber-700">{atom.note}</p>}
        {parent && (
          <button
            type="button"
            onClick={() => go(parent)}
            className="text-left text-[12.5px] text-teal-700 hover:underline"
          >
            {atom.included_in
              ? t("Part of: {label}", { label: parent.label })
              : t("Same charge as: {label}", { label: parent.label })}
          </button>
        )}
        {related.length > 0 && (
          <div>
            <div className="text-[12px] text-subtle">{t("Linked items (shown, not added)")}</div>
            <ul className="mt-1 space-y-1">
              {related.map((c) => (
                <li key={c.id}>
                  <button
                    type="button"
                    onClick={() => go(c)}
                    className="flex w-full justify-between gap-2 text-[12.5px] hover:text-teal-700"
                  >
                    <span className="text-muted">{c.fee_label}</span>
                    <span className="num">{chf(c.amount, 2)}</span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
      {atom.evidence?.length ? (
        <SourcePane evidence={atom.evidence} usedIn={usedIn} />
      ) : (
        <div className="rounded-md border border-dashed border-line-strong p-5 text-center text-[13px] text-muted">
          {atom.measurement === "unknown"
            ? t("No document contains this cost yet. See the document request list for what would resolve it.")
            : t("This value comes from proposal inputs, not from a client document.")}
        </div>
      )}
    </div>
  );
}

/** The inputs of a number: a readable crop of where each is written, the full page on demand, and its decision trail. */
export function SourcePane({ evidence, usedIn }: { evidence: EvidenceRef[]; usedIn?: string[] }) {
  const pid = Number(useParams().id);
  const [idx, setIdx] = useState(0);
  const [full, setFull] = useState(false);
  const e = evidence[Math.min(idx, evidence.length - 1)];
  const facts = useQuery({
    queryKey: ["facts", e.document_id],
    queryFn: () => api.facts(e.document_id),
    enabled: full || !!e.sheet,
  });
  return (
    <div className="min-w-0 space-y-4">
      {evidence.length > 1 && (
        <ul className="space-y-1.5" aria-label={t("Inputs")}>
          {evidence.map((x, i) => (
            <li key={`${x.fact_id}-${x.role}`}>
              <button
                type="button"
                aria-pressed={i === idx}
                onClick={() => setIdx(i)}
                className={cn(
                  "w-full rounded-md border px-3 py-2 text-left text-[12.5px]",
                  i === idx ? "border-teal-700/50 bg-teal-50" : "border-line hover:bg-paper",
                )}
              >
                <div className="flex items-baseline justify-between gap-2">
                  <span className="text-subtle">{t(ROLE_LABEL[x.role])}</span>
                  <span className="num font-medium text-ink">{fmtValue(x)}</span>
                </div>
                <div className="truncate text-muted">
                  {x.where} · {x.label}
                </div>
              </button>
            </li>
          ))}
        </ul>
      )}
      <section aria-label={t("Where it is written")} className="space-y-2">
        <div className="flex items-baseline justify-between gap-2">
          <h4 className="text-[11.5px] font-semibold uppercase tracking-wider text-subtle">
            {t("Where it is written")}
          </h4>
          {!e.sheet && e.page && (
            <button
              type="button"
              onClick={() => setFull(!full)}
              className="flex items-center gap-1 text-[12.5px] text-teal-700 hover:underline"
            >
              {full ? <Minimize2 className="h-3.5 w-3.5" /> : <Maximize2 className="h-3.5 w-3.5" />}
              {full ? t("Show the row only") : t("Show full page")}
            </button>
          )}
        </div>
        <div className="truncate text-[12.5px] font-medium text-ink" title={e.where}>
          {e.where}
        </div>
        {e.sheet ? (
          <div className="h-[260px] overflow-hidden rounded-md border border-line">
            {facts.data ? (
              <SheetEvidence docId={e.document_id} facts={facts.data} activeId={e.fact_id} />
            ) : (
              <Spinner label={t("Locating source")} />
            )}
          </div>
        ) : full ? (
          <div className="h-[560px] overflow-hidden rounded-md border border-line">
            {facts.data ? (
              <PdfEvidence docId={e.document_id} facts={facts.data} activeId={e.fact_id} page={e.page ?? 1} focus />
            ) : (
              <Spinner label={t("Locating source")} />
            )}
          </div>
        ) : e.page && e.bbox ? (
          <SourceCrop key={e.fact_id} docId={e.document_id} page={e.page} bbox={e.bbox} tag={fmtValue(e)} />
        ) : (
          <p className="text-[12.5px] text-muted">{t("No position on the page was recorded for this value.")}</p>
        )}
        {e.snippet && (
          <p className="break-words font-mono text-[12px] text-ink" title={e.snippet}>
            “{e.snippet}”
          </p>
        )}
        {e.status === "corrected" && e.value_extracted && (
          <p className="text-[12px] text-muted">{t("read as {v}", { v: e.value_extracted })}</p>
        )}
      </section>
      <DecisionTrail e={e} usedIn={e.role === "value" ? usedIn : undefined} />
      <Link to={`/p/${pid}/review?doc=${e.document_id}&fact=${e.fact_id}`}>
        <Button variant="outline" size="sm">
          <ExternalLink className="h-3.5 w-3.5" /> {t("Open in evidence review")}
        </Button>
      </Link>
    </div>
  );
}
