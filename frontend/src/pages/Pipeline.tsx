import { PageTitle } from "@/components/Shell";
import { Badge, Button, Card, ErrorBox, InfoTip, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { DOC_TYPES, LAYER, chf, cn, num } from "@/lib/format";
import { t } from "@/lib/i18n";
import type { PipelineStage, StageStatus } from "@/lib/types";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, ChevronDown, CircleDashed, XCircle } from "lucide-react";
import { type ReactNode, useState } from "react";
import { Link, useParams } from "react-router-dom";

/** Title and a plain-language "what happens here" for each stage, in pipeline order. */
const STAGES: Record<string, { title: string; help: string }> = {
  upload: {
    title: "Upload and fingerprint",
    help: "The file is checked (type, size, no macros) and stored on this server. Its SHA-256 fingerprint proves later that the figures come from this exact file.",
  },
  read: {
    title: "Reading the text",
    help: "Digital PDFs are read directly, with the position of every word. Scanned pages are read with OCR on this server; OCR values always need a human check.",
  },
  classify: {
    title: "Recognising the document",
    help: "Keywords decide what the document is (statement, cost report, price list, KID…), who issued it, its currency and its dates. You can correct the type on the Documents page.",
  },
  extract: {
    title: "Finding the values",
    help: "Holdings, totals, fees and product costs are read with the page and the exact box where each value is printed. Nothing is invented: a value that is not printed is not extracted.",
  },
  review: {
    title: "Human review",
    help: "An analyst accepts, corrects or rejects each value against the original. Corrections keep their history.",
  },
  validate: {
    title: "Cross-checks",
    help: "Values are checked against each other: positions add up to the printed total, fees match the price list of the booking bank, cash debits match the cost report.",
  },
  categorize: {
    title: "Cost layers",
    help: "Each cost is placed in its layer (service, custody, trading, funds…). A cost that is already inside another one, such as a management fee inside the fund's ongoing charges, is shown but counted only once.",
  },
  result: {
    title: "Effect on the total",
    help: "What this document adds to the known annual cost. Missing costs stay visible as unknown, never zero.",
  },
};

const STATUS: Record<StageStatus, { label: string; tone: string; Icon: typeof CheckCircle2 }> = {
  ok: { label: "Done", tone: "teal", Icon: CheckCircle2 },
  warn: { label: "Check", tone: "amber", Icon: AlertTriangle },
  fail: { label: "Problem", tone: "red", Icon: XCircle },
  skipped: { label: "Not applicable", tone: "grey", Icon: CircleDashed },
};

const ROLE: Record<string, string> = {
  counted: "Counted in the total",
  included_in_parent: "Already inside another cost: counted once",
  corroborating: "Confirms another figure: not added again",
  not_a_paid_cost: "Information only: not a cost paid",
  unknown: "Amount unknown: not zero",
};

const REVIEW: Record<string, string> = {
  extracted: "Waiting",
  accepted: "Accepted",
  corrected: "Corrected",
  rejected: "Rejected",
  manual: "Added by hand",
};

export default function PipelinePage() {
  const { id, did } = useParams();
  const q = useQuery({ queryKey: ["pipeline", Number(did)], queryFn: () => api.pipeline(Number(did)) });
  if (q.isLoading) return <Spinner />;
  if (q.error || !q.data) return <ErrorBox error={q.error} />;
  const p = q.data;
  return (
    <div className="max-w-4xl">
      <PageTitle
        title={t("How this document was processed")}
        subtitle={t(
          "Every step from upload to the cost figure, with its result, time taken and anything to check. Open a step for details.",
        )}
        actions={
          <>
            <Link to={`/p/${id}/review?doc=${p.document.id}`}>
              <Button variant="accent">{t("Review its values")}</Button>
            </Link>
            <Link to={`/p/${id}/documents`}>
              <Button>{t("All documents")}</Button>
            </Link>
          </>
        }
      />
      <div className="mb-4 flex flex-wrap items-center gap-2 text-[13px] text-muted">
        <span className="break-all font-semibold text-navy-900">{p.document.filename}</span>
        <Badge>{t(DOC_TYPES[p.document.doc_type] ?? p.document.doc_type)}</Badge>
        {p.total_ms !== null && <span className="num">{t("{ms} ms in total", { ms: p.total_ms })}</span>}
      </div>
      <ol className="space-y-3">
        {p.stages.map((s, i) => (
          <StageCard key={s.key} n={i + 1} s={s} />
        ))}
      </ol>
    </div>
  );
}

function StageCard({ n, s }: { n: number; s: PipelineStage }) {
  const meta = STAGES[s.key] ?? { title: s.key, help: "" };
  const st = STATUS[s.status];
  const vars = s.key === "classify" ? { ...s.vars, type: t(DOC_TYPES[String(s.vars.type)] ?? "") } : s.vars;
  const [open, setOpen] = useState(false);
  const hasMore = s.details.length || s.values?.length || s.checks?.length || s.atoms?.length;
  return (
    <li>
      <Card className="px-5 py-4" id={`stage-${s.key}`}>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex min-w-0 items-start gap-3">
            <span className="num mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-navy-100 text-[12px] font-semibold text-navy-800">
              {n}
            </span>
            <div className="min-w-0">
              <div className="flex items-center gap-1.5">
                <h3 className="text-[14.5px] font-semibold text-navy-900">{t(meta.title)}</h3>
                {meta.help && <InfoTip>{t(meta.help)}</InfoTip>}
              </div>
              <p className="mt-0.5 text-[13.5px] text-ink">{t(s.summary, vars)}</p>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            {s.ms !== null && <span className="num text-[12px] text-subtle">{s.ms} ms</span>}
            <Badge tone={st.tone}>
              <st.Icon className="h-3 w-3" aria-hidden />
              {t(st.label)}
            </Badge>
          </div>
        </div>
        {s.warnings?.map((w) => (
          <div key={w} className="ml-9 mt-2 flex items-start gap-1.5 text-[12.5px] text-amber-700">
            <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden /> {w}
          </div>
        ))}
        {hasMore ? (
          <div className="ml-9 mt-2">
            <button
              type="button"
              aria-expanded={open}
              onClick={() => setOpen(!open)}
              className="flex items-center gap-1 text-[12.5px] font-medium text-teal-700 hover:underline"
            >
              <ChevronDown className={cn("h-3.5 w-3.5 transition-transform", open && "rotate-180")} aria-hidden />
              {open ? t("Hide details") : t("Show details")}
            </button>
            {open && (
              <div className="mt-2 rounded-md bg-paper px-3 py-2.5">
                <StageDetails s={s} />
              </div>
            )}
          </div>
        ) : null}
      </Card>
    </li>
  );
}

function StageDetails({ s }: { s: PipelineStage }) {
  return (
    <div className="space-y-3 text-[12.5px]">
      {s.details.length > 0 && (
        <dl className="grid grid-cols-[minmax(0,180px)_1fr] gap-x-4 gap-y-1">
          {s.details.map((d) => (
            <div key={d.label} className="contents">
              <dt className="text-muted">{pageLabel(d.label)}</dt>
              <dd className="break-all font-mono text-[12px] text-ink">{d.value}</dd>
            </div>
          ))}
        </dl>
      )}
      {s.values && s.values.length > 0 && (
        <Table head={[t("Value"), t("Where"), t("Review"), t("Amount")]}>
          {s.values.map((v) => (
            <tr key={v.id} className="border-t border-line">
              <td className="py-1 pr-3">{v.label}</td>
              <td className="py-1 pr-3 font-mono text-[11.5px] text-subtle">{v.where}</td>
              <td className="py-1 pr-3 text-muted">{t(REVIEW[v.status] ?? v.status)}</td>
              <td className="num py-1 text-right whitespace-nowrap">
                {v.value === null ? "–" : num(v.value, 2)} {v.currency ?? ""}
              </td>
            </tr>
          ))}
        </Table>
      )}
      {s.checks?.map((c) => (
        <div key={c.title} className="flex items-start gap-2">
          {c.status === "pass" ? (
            <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-teal-700" aria-label={t("Passed")} />
          ) : c.status === "fail" ? (
            <XCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-red-700" aria-label={t("Problem")} />
          ) : (
            <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-700" aria-label={t("Check")} />
          )}
          <div>
            <div className="text-ink">{c.title}</div>
            <div className="text-muted">{c.detail}</div>
          </div>
        </div>
      ))}
      {s.atoms && s.atoms.length > 0 && (
        <Table head={[t("Cost"), t("Layer"), t("How it counts"), t("Per year")]}>
          {s.atoms.map((a) => (
            <tr key={`${a.label}-${a.fee_label}`} className="border-t border-line align-top">
              <td className="py-1 pr-3">
                <div>{a.fee_label}</div>
                <div className="text-[11.5px] text-subtle">{a.formula}</div>
              </td>
              <td className="py-1 pr-3">{t(LAYER[a.layer]?.short ?? a.layer)}</td>
              <td className="py-1 pr-3">{t(ROLE[a.role] ?? a.role)}</td>
              <td className="num py-1 text-right">{a.amount === null ? t("unknown") : chf(a.amount)}</td>
            </tr>
          ))}
        </Table>
      )}
    </div>
  );
}

/** Backend sends "Page 3": translate the word, keep the number. */
function pageLabel(label: string): string {
  const m = /^Page (\d+)$/.exec(label);
  return m ? t("Page {n}", { n: m[1] }) : t(label);
}

function Table({ head, children }: { head: string[]; children: ReactNode }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="text-left text-[11px] uppercase tracking-wide text-subtle">
            {head.map((h, i) => (
              <th
                key={h}
                className={i === head.length - 1 ? "pb-1 pr-3 text-right font-medium" : "pb-1 pr-3 font-medium"}
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}
