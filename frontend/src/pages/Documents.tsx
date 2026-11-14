import { PageTitle } from "@/components/Shell";
import { Badge, Button, Card, CardHeader, Empty, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { DOC_TYPES, assets, cn } from "@/lib/format";
import { t } from "@/lib/i18n";
import { isOcrEngine } from "@/lib/trail";
import type { Analysis, DocumentRow } from "@/lib/types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  ChevronRight,
  CircleDashed,
  Clock,
  FileSpreadsheet,
  FileText,
  Loader2,
  ScanLine,
  UploadCloud,
  Workflow,
  XCircle,
} from "lucide-react";
import { Fragment, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";

/** Files sent at once. The server caps real parallel work at its CPU count; more requests only queue. */
const UPLOADS_AT_ONCE = 3;

export default function DocumentsPage() {
  const pid = Number(useParams().id);
  const qc = useQueryClient();
  const docs = useQuery({ queryKey: ["documents", pid], queryFn: () => api.documents(pid) });
  const analysis = useQuery({ queryKey: ["analysis", pid], queryFn: () => api.analysis(pid) });
  const [rows, setRows] = useState<UploadRow[]>([]);
  const busy = rows.some((r) => r.state === "waiting" || r.state === "reading");
  // One request per file, up to UPLOADS_AT_ONCE at a time (the server reads them in parallel, SC-5.20):
  // each row moves on as its own document finishes, in whatever order that happens.
  const uploadAll = async (files: File[]) => {
    const start = rows.length;
    setRows((r) => [...r, ...files.map((f) => ({ filename: f.name, state: "waiting" as const }))]);
    let next = 0;
    const worker = async () => {
      while (next < files.length) {
        const i = next++;
        const at = start + i;
        const set = (patch: Partial<UploadRow>) =>
          setRows((r) => r.map((row, j) => (j === at ? { ...row, ...patch } : row)));
        set({ state: "reading" });
        try {
          const res = (await api.upload(pid, [files[i]])).results[0];
          set({ state: "done", ...res });
        } catch (e) {
          set({ state: "done", status: "rejected", error: e instanceof Error ? e.message : String(e) });
        }
        await qc.invalidateQueries({ queryKey: ["documents", pid] });
      }
    };
    await Promise.all(Array.from({ length: Math.min(UPLOADS_AT_ONCE, files.length) }, worker));
    qc.invalidateQueries();
  };
  const setType = useMutation({
    mutationFn: ({ id, t }: { id: number; t: string }) => api.setDocType(id, t),
    onSuccess: () => qc.invalidateQueries(),
  });
  return (
    <div>
      <PageTitle
        title={t("Documents")}
        subtitle={t(
          "Upload everything the prospect has: statements from each bank, annual cost reports, cash statements, fee agreements and product KIDs. Files are processed on this machine only.",
        )}
        actions={
          <Link to={`/p/${pid}/review`}>
            <Button>{t("Review extracted values")}</Button>
          </Link>
        }
      />
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_300px]">
        <div className="space-y-4">
          <Dropzone onFiles={uploadAll} busy={busy} compact={!!docs.data?.length} />
          {rows.length > 0 && <UploadProgress rows={rows} docs={docs.data ?? []} pid={pid} busy={busy} />}
          <Card>
            <CardHeader
              title={t("Uploaded documents")}
              subtitle={t(
                "Type, bank, jurisdiction and dates are detected automatically. Correct the type if it is wrong; the document is re-read.",
              )}
            />
            {docs.isLoading ? (
              <Spinner />
            ) : !docs.data?.length ? (
              <Empty icon={<FileText className="h-8 w-8" />} title={t("No documents yet")}>
                {t("Drop PDF or Excel files above.")}
              </Empty>
            ) : (
              <DocTable docs={docs.data} pid={pid} onType={(id, t) => setType.mutate({ id, t })} />
            )}
          </Card>
        </div>
        <Checklist analysis={analysis.data} docs={docs.data ?? []} />
      </div>
    </div>
  );
}

type UploadRow = {
  filename: string;
  state: "waiting" | "reading" | "done";
  status?: string;
  error?: string;
  doc_type?: string;
  document_id?: number;
};

/** Live list of the files in this upload: each row moves waiting → reading → result, then a next step. */
function UploadProgress({
  rows,
  docs,
  pid,
  busy,
}: { rows: UploadRow[]; docs: DocumentRow[]; pid: number; busy: boolean }) {
  const done = rows.filter((r) => r.state === "done").length;
  const facts = (id?: number) => docs.find((d) => d.id === id)?.fact_count;
  const toCheck = rows.filter((r) => r.status === "needs_review").length;
  return (
    <Card>
      <CardHeader
        title={busy ? t("Reading documents…") : t("Upload finished")}
        actions={
          <span className="num text-[12.5px] text-muted">
            {t("{done} of {n} files processed", { done, n: rows.length })}
          </span>
        }
      />
      <div className="mx-5 mb-1 h-1.5 overflow-hidden rounded-full bg-paper" aria-hidden>
        <div className="h-full bg-teal-600 transition-all" style={{ width: `${(done / rows.length) * 100}%` }} />
      </div>
      <ul className="divide-y divide-line text-[13px]" aria-live="polite">
        {rows.map((r, i) => (
          <li key={i} className="flex items-center justify-between gap-3 px-5 py-2">
            <span className="flex min-w-0 items-center gap-2">
              {r.state === "waiting" ? (
                <Clock className="h-4 w-4 shrink-0 text-subtle" />
              ) : r.state === "reading" ? (
                <Loader2 className="h-4 w-4 shrink-0 animate-spin text-teal-700" />
              ) : r.status === "rejected" ? (
                <XCircle className="h-4 w-4 shrink-0 text-red-700" />
              ) : r.status === "needs_review" ? (
                <AlertTriangle className="h-4 w-4 shrink-0 text-amber-700" />
              ) : (
                <CheckCircle2 className="h-4 w-4 shrink-0 text-teal-700" />
              )}
              <span className="truncate">{r.filename}</span>
            </span>
            <span className="shrink-0">
              {r.state === "waiting" ? (
                <span className="text-subtle">{t("Waiting")}</span>
              ) : r.state === "reading" ? (
                <span className="text-teal-700">{t("Reading, classifying, extracting…")}</span>
              ) : r.status === "rejected" ? (
                <Badge tone="red">{r.error}</Badge>
              ) : r.status === "duplicate" ? (
                <Badge>{t("Already uploaded (same SHA-256)")}</Badge>
              ) : (
                <span className="flex items-center gap-2">
                  <Badge tone={r.status === "needs_review" ? "amber" : "teal"}>
                    {t(DOC_TYPES[r.doc_type ?? "unknown"])}
                  </Badge>
                  <span className="num text-muted">{t("{n} values read", { n: facts(r.document_id) ?? "…" })}</span>
                  {r.status === "needs_review" && <span className="text-amber-700">· {t("check type")}</span>}
                </span>
              )}
            </span>
          </li>
        ))}
      </ul>
      {!busy && (
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line px-5 py-3">
          <span className="text-[12.5px] text-muted">
            {toCheck
              ? t("{n} documents need a quick check. Next: confirm the values read, each shown on its page.", {
                  n: toCheck,
                })
              : t("Next: confirm the values read, each shown on its page.")}
          </span>
          <span className="flex gap-2">
            <Link to={`/p/${pid}/review`}>
              <Button>
                {t("Review values")} <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
            <Link to={`/p/${pid}/costs`}>
              <Button variant="outline">{t("See costs")}</Button>
            </Link>
          </span>
        </div>
      )}
    </Card>
  );
}

/** Full height until the first document; then one line, so the list is what the analyst sees. */
function Dropzone({ onFiles, busy, compact }: { onFiles: (f: File[]) => void; busy: boolean; compact: boolean }) {
  const ref = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setOver(false);
        const files = Array.from(e.dataTransfer.files);
        if (files.length) onFiles(files);
      }}
      className={cn(
        "flex items-center gap-2 rounded-[var(--radius-card)] border-2 border-dashed transition-colors",
        compact ? "flex-wrap px-5 py-3" : "flex-col justify-center px-6 py-8 text-center",
        over ? "border-teal-600 bg-teal-50" : "border-line-strong bg-surface",
      )}
    >
      <UploadCloud className={cn("shrink-0 text-teal-700", compact ? "h-5 w-5" : "h-8 w-8")} />
      <div className={cn("min-w-0", compact && "flex-1")}>
        <div className={cn("font-semibold text-navy-900", compact ? "text-[13.5px]" : "text-[15px]")}>
          {t(compact ? "Add more documents" : "Drop documents here")}
        </div>
        <div className="text-[12.5px] text-muted">
          {t("PDF (digital or scanned, OCR in EN/DE/FR/IT) or XLSX · max 25 MB each · duplicates are detected")}
        </div>
      </div>
      <input
        ref={ref}
        type="file"
        multiple
        accept=".pdf,.xlsx"
        className="sr-only"
        aria-label={t("Choose files to upload")}
        onChange={(e) => {
          const files = Array.from(e.target.files ?? []);
          if (files.length) onFiles(files);
          e.target.value = "";
        }}
      />
      <Button
        className={compact ? undefined : "mt-2"}
        variant={compact ? "outline" : "primary"}
        onClick={() => ref.current?.click()}
        loading={busy}
      >
        {t("Choose files")}
      </Button>
    </div>
  );
}

const SHOWN = 6;

/** One line per document; how it was read, warnings and the type selector open under the row. */
function DocTable({
  docs,
  pid,
  onType,
}: { docs: DocumentRow[]; pid: number; onType: (id: number, t: string) => void }) {
  const [all, setAll] = useState(false);
  const [open, setOpen] = useState<number | null>(null);
  // Documents that need a check first, so they are never hidden behind "Show all".
  const sorted = [...docs].sort((x, y) => Number(y.status === "needs_review") - Number(x.status === "needs_review"));
  const shown = all ? sorted : sorted.slice(0, SHOWN);
  return (
    <div>
      <table className="w-full table-fixed text-[13px]">
        <thead>
          <tr className="whitespace-nowrap border-b border-line text-left text-[11.5px] uppercase tracking-wide text-subtle">
            <th className="px-3 py-2 font-medium sm:px-5">{t("File")}</th>
            <th className="hidden w-[15%] px-3 py-2 font-medium min-[1360px]:table-cell">{t("Type")}</th>
            <th className="hidden w-[15%] px-3 py-2 font-medium min-[1360px]:table-cell">{t("Bank or issuer")}</th>
            <th className="hidden w-[112px] px-3 py-2 font-medium sm:table-cell">{t("Date")}</th>
            <th className="w-[64px] px-3 py-2 text-right font-medium">{t("Values")}</th>
            <th className="w-[76px] px-3 py-2 font-medium sm:w-[148px]">{t("Status")}</th>
          </tr>
        </thead>
        <tbody>
          {shown.map((d) => {
            const isOpen = open === d.id;
            const check = d.status === "needs_review";
            return (
              <Fragment key={d.id}>
                <tr className={cn("border-b border-line hover:bg-paper", isOpen && "bg-paper")}>
                  <td className="px-3 py-2 sm:px-5">
                    <button
                      type="button"
                      aria-expanded={isOpen}
                      onClick={() => setOpen(isOpen ? null : d.id)}
                      aria-label={t(isOpen ? "Hide details of {file}" : "Show details of {file}", { file: d.filename })}
                      className="flex w-full min-w-0 items-center gap-2 text-left font-medium text-navy-900"
                    >
                      <ChevronRight className={cn("h-3.5 w-3.5 shrink-0 text-subtle", isOpen && "rotate-90")} />
                      {d.filename.endsWith(".xlsx") ? (
                        <FileSpreadsheet className="h-4 w-4 shrink-0 text-teal-700" />
                      ) : (
                        <FileText className="h-4 w-4 shrink-0 text-navy-700" />
                      )}
                      <span className="min-w-0">
                        <span className="block truncate" title={d.filename}>
                          {d.filename}
                        </span>
                        <span className="block truncate text-[12px] font-normal text-muted min-[1360px]:hidden">
                          {t(DOC_TYPES[d.doc_type] ?? d.doc_type_label)}
                          {d.profile.institution && ` · ${d.profile.institution}`}
                        </span>
                      </span>
                    </button>
                  </td>
                  <td className="hidden truncate px-3 py-2 text-ink min-[1360px]:table-cell">
                    {t(DOC_TYPES[d.doc_type] ?? d.doc_type_label)}
                  </td>
                  <td
                    className="hidden truncate px-3 py-2 text-ink min-[1360px]:table-cell"
                    title={d.profile.institution ?? undefined}
                  >
                    {d.profile.institution ?? <span className="text-subtle">{t("not found")}</span>}
                  </td>
                  <td className="num hidden truncate px-3 py-2 text-muted sm:table-cell">
                    {d.profile.period_end ?? d.profile.as_of ?? "–"}
                  </td>
                  <td className="num px-3 py-2 text-right">{d.fact_count}</td>
                  <td className="px-3 py-2">
                    <span className="flex items-center justify-between gap-1">
                      {check ? (
                        <Badge tone="amber" className="relative">
                          <AlertTriangle className="h-3 w-3" aria-hidden />
                          <span className="sr-only sm:not-sr-only">{t("Needs a check")}</span>
                        </Badge>
                      ) : (
                        <Badge tone="teal" className="relative">
                          <CheckCircle2 className="h-3 w-3" aria-hidden />
                          <span className="sr-only sm:not-sr-only">{t("Ready")}</span>
                        </Badge>
                      )}
                      <Link
                        to={`/p/${pid}/documents/${d.id}`}
                        aria-label={t("How it was processed")}
                        title={t("How it was processed")}
                        className="rounded-[var(--radius-control)] p-1 text-teal-700 hover:bg-teal-50"
                      >
                        <Workflow className="h-4 w-4" />
                      </Link>
                    </span>
                  </td>
                </tr>
                {isOpen && <DocDetails d={d} pid={pid} onType={onType} />}
              </Fragment>
            );
          })}
        </tbody>
      </table>
      {docs.length > SHOWN && (
        <div className="border-t border-line px-5 py-2.5">
          <Button variant="ghost" size="sm" onClick={() => setAll(!all)}>
            {all ? t("Show fewer") : t("Show all {n} documents", { n: docs.length })}
          </Button>
        </div>
      )}
    </div>
  );
}

function DocDetails({ d, pid, onType }: { d: DocumentRow; pid: number; onType: (id: number, t: string) => void }) {
  const period = d.profile.period_start ? `${d.profile.period_start} → ${d.profile.period_end}` : d.profile.as_of;
  return (
    <tr className="border-b border-line bg-paper">
      <td colSpan={6} className="px-5 pb-3 pt-1">
        <dl className="grid gap-x-6 gap-y-2 pl-6 text-[12.5px] sm:grid-cols-[repeat(auto-fit,minmax(180px,1fr))]">
          <div>
            <dt className="text-subtle">{t("Read with")}</dt>
            <dd className="mt-0.5">
              {d.profile.engines.some(isOcrEngine) ? (
                <Badge tone="violet">
                  <ScanLine className="h-3 w-3" /> OCR
                </Badge>
              ) : d.profile.engines.includes("openpyxl") ? (
                <Badge>{t("Spreadsheet cells")}</Badge>
              ) : (
                <Badge>{t("Digital text")}</Badge>
              )}
              <span className="num ml-2 text-muted">
                {d.profile.page_count === 1 ? t("1 page") : t("{n} pages", { n: d.profile.page_count })}
              </span>
            </dd>
          </div>
          <div>
            <dt className="text-subtle">{t("Period or date")}</dt>
            <dd className="num mt-0.5 text-ink">
              {period ?? "–"}
              {d.profile.jurisdiction && <Badge className="ml-1.5">{d.profile.jurisdiction}</Badge>}
            </dd>
          </div>
          <div>
            <dt className="text-subtle">{t("Fingerprint")}</dt>
            <dd className="mt-0.5 font-mono text-muted" title={`sha256 ${d.sha256}`}>
              {d.sha256.slice(0, 12)}
            </dd>
          </div>
          <div>
            <dt className="text-subtle">
              <label htmlFor={`type-${d.id}`}>{t("Document type")}</label>
            </dt>
            <dd className="mt-0.5">
              <select
                id={`type-${d.id}`}
                aria-label={t("Document type for {file}", { file: d.filename })}
                className="h-8 rounded-[var(--radius-control)] border border-line-strong bg-surface px-2 text-[12.5px]"
                value={d.doc_type}
                onChange={(e) => onType(d.id, e.target.value)}
              >
                {Object.entries(DOC_TYPES).map(([k, v]) => (
                  <option key={k} value={k}>
                    {t(v)}
                  </option>
                ))}
              </select>
              {d.doc_type !== d.detected_type && <span className="ml-2 text-subtle">{t("set manually")}</span>}
            </dd>
          </div>
        </dl>
        {d.profile.warnings.map((w) => (
          <div key={w} className="ml-6 mt-2 flex items-start gap-1 text-[12px] text-amber-700">
            <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0" /> {w}
          </div>
        ))}
        <div className="ml-6 mt-3 flex gap-4 text-[12.5px] font-medium">
          <Link to={`/p/${pid}/review?doc=${d.id}`} className="text-teal-700 hover:underline">
            {t("Check its values")} →
          </Link>
          <Link to={`/p/${pid}/documents/${d.id}`} className="text-teal-700 hover:underline">
            {t("How it was processed")} →
          </Link>
        </div>
      </td>
    </tr>
  );
}

function Checklist({ analysis, docs }: { analysis?: Analysis; docs: DocumentRow[] }) {
  const has = (t: string, inst: string) =>
    docs.some((d) => d.doc_type === t && (d.profile.institution ?? "").includes(inst));
  const funds = analysis?.holdings.filter((h) => ["FUND", "ETF", "STRUCTURED"].includes(h.asset_class)) ?? [];
  const covered = funds.filter((h) =>
    docs.some((d) => (d.doc_type === "kid" || d.doc_type === "termsheet") && h.isin && d.filename.includes(h.isin)),
  );
  const kidIsins = new Set(
    docs
      .filter((d) => d.doc_type === "kid" || d.doc_type === "termsheet")
      .flatMap((d) => d.filename.match(/[A-Z]{2}[A-Z0-9]{9}\d/g) ?? []),
  );
  return (
    <Card className="h-fit">
      <CardHeader
        title={t("What we need")}
        subtitle={t("Per bank and per product. Missing items stay visible in the cost view.")}
      />
      <div className="space-y-4 px-5 py-4 text-[13px]">
        {!analysis?.institutions.length && <p className="text-muted">{t("Upload a statement of assets to start.")}</p>}
        {analysis?.institutions.map((i) => {
          const key = i.name.split(" (")[0];
          return (
            <div key={i.name}>
              <div className="mb-1.5 flex items-center justify-between">
                <span className="font-semibold text-navy-900">{i.name}</span>
                <span className="num text-[12px] text-subtle">
                  {assets(
                    i.assets,
                    analysis.holdings.some((h) => h.institution === i.name),
                    t("Not valued yet"),
                  )}
                </span>
              </div>
              <Item ok={has("portfolio_statement", key)} label={t("Statement of assets")} required />
              <Item ok={has("cost_report", key)} label={t("Annual costs & charges report")} required />
              <Item ok={has("cash_statement", key)} label={t("Cash statement (fee debits)")} />
              <Item
                ok={analysis.checks.some(
                  (c) => c.title.startsWith(i.name) && c.title.includes("price schedule applies"),
                )}
                warn={analysis.checks.some((c) => c.title.startsWith(i.name) && c.status === "fail")}
                label={t("Fee agreement / price schedule (booking entity)")}
              />
            </div>
          );
        })}
        {funds.length > 0 && (
          <div>
            <div className="mb-1.5 flex items-center justify-between">
              <span className="font-semibold text-navy-900">{t("Product documents")}</span>
              <span className="text-[12px] text-subtle">
                {kidIsins.size ? funds.filter((f) => f.isin && kidIsins.has(f.isin)).length : covered.length}/
                {funds.length}
              </span>
            </div>
            {funds.map((f) => (
              <Item
                key={f.fact_id}
                ok={!!f.isin && kidIsins.has(f.isin)}
                label={`${f.name}`}
                sub={f.isin ?? undefined}
                required
              />
            ))}
          </div>
        )}
      </div>
    </Card>
  );
}

function Item({
  ok,
  warn,
  label,
  sub,
  required,
}: { ok: boolean; warn?: boolean; label: string; sub?: string; required?: boolean }) {
  return (
    <div className="flex items-start gap-2 py-1">
      {ok ? (
        <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-teal-700" />
      ) : warn ? (
        <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-700" />
      ) : (
        <CircleDashed className={cn("mt-0.5 h-4 w-4 shrink-0", required ? "text-amber-700" : "text-subtle")} />
      )}
      <div className="min-w-0">
        <div className={cn(ok ? "text-ink" : required ? "text-amber-700" : "text-muted")}>
          {label}
          {!ok && !required && <span className="text-subtle"> · {t("optional")}</span>}
          {warn && <span className="text-red-700"> · {t("wrong entity")}</span>}
        </div>
        {sub && <div className="font-mono text-[11px] text-subtle">{sub}</div>}
      </div>
    </div>
  );
}
