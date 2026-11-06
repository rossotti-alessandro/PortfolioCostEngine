import { PageTitle } from "@/components/Shell";
import { Badge, Button, Card, CardHeader, Empty, ErrorBox, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { DOC_TYPES, chf, cn } from "@/lib/format";
import { t } from "@/lib/i18n";
import type { Analysis, DocumentRow } from "@/lib/types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  CircleDashed,
  FileSpreadsheet,
  FileText,
  ScanLine,
  UploadCloud,
  XCircle,
} from "lucide-react";
import { useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";

export default function DocumentsPage() {
  const pid = Number(useParams().id);
  const qc = useQueryClient();
  const docs = useQuery({ queryKey: ["documents", pid], queryFn: () => api.documents(pid) });
  const analysis = useQuery({ queryKey: ["analysis", pid], queryFn: () => api.analysis(pid) });
  const [results, setResults] = useState<{ filename: string; status: string; error?: string; doc_type?: string }[]>([]);
  const upload = useMutation({
    mutationFn: (files: File[]) => api.upload(pid, files),
    onSuccess: (r) => {
      setResults(r.results);
      qc.invalidateQueries();
    },
  });
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
            <Button variant="accent">{t("Review extracted values")}</Button>
          </Link>
        }
      />
      <div className="grid gap-4 lg:grid-cols-[1fr_380px]">
        <div className="space-y-4">
          <Dropzone onFiles={(f) => upload.mutate(f)} busy={upload.isPending} />
          {upload.error && <ErrorBox error={upload.error} />}
          {results.length > 0 && (
            <Card>
              <CardHeader title={t("Last upload")} />
              <ul className="divide-y divide-line text-[13px]">
                {results.map((r) => (
                  <li key={r.filename} className="flex items-center justify-between gap-3 px-5 py-2">
                    <span className="truncate">{r.filename}</span>
                    {r.status === "rejected" ? (
                      <Badge tone="red">{r.error}</Badge>
                    ) : r.status === "duplicate" ? (
                      <Badge>{t("Already uploaded (same SHA-256)")}</Badge>
                    ) : r.status === "needs_review" ? (
                      <Badge tone="amber">
                        {t("Needs review")} · {t(DOC_TYPES[r.doc_type ?? "unknown"])}
                      </Badge>
                    ) : (
                      <Badge tone="teal">
                        {t("Extracted")} · {t(DOC_TYPES[r.doc_type ?? "unknown"])}
                      </Badge>
                    )}
                  </li>
                ))}
              </ul>
            </Card>
          )}
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

function Dropzone({ onFiles, busy }: { onFiles: (f: File[]) => void; busy: boolean }) {
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
        "flex flex-col items-center justify-center gap-2 rounded-[var(--radius-card)] border-2 border-dashed px-6 py-8 text-center transition-colors",
        over ? "border-teal-600 bg-teal-50" : "border-line-strong bg-surface",
      )}
    >
      <UploadCloud className="h-8 w-8 text-teal-700" />
      <div className="text-[15px] font-semibold text-navy-900">{t("Drop documents here")}</div>
      <div className="text-[13px] text-muted">
        {t("PDF (digital or scanned, OCR in EN/DE/FR/IT) or XLSX · max 25 MB each · duplicates are detected")}
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
      <Button className="mt-2" onClick={() => ref.current?.click()} loading={busy}>
        {t("Choose files")}
      </Button>
    </div>
  );
}

function DocTable({
  docs,
  pid,
  onType,
}: { docs: DocumentRow[]; pid: number; onType: (id: number, t: string) => void }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-[13px]">
        <thead>
          <tr className="border-b border-line text-left text-[11.5px] uppercase tracking-wide text-subtle">
            <th className="px-5 py-2 font-medium">{t("File")}</th>
            <th className="px-3 py-2 font-medium">{t("Type")}</th>
            <th className="px-3 py-2 font-medium">{t("Issuer")}</th>
            <th className="px-3 py-2 font-medium">{t("Date / period")}</th>
            <th className="px-3 py-2 font-medium">{t("Read with")}</th>
            <th className="px-3 py-2 text-right font-medium">{t("Values")}</th>
          </tr>
        </thead>
        <tbody>
          {docs.map((d) => (
            <tr key={d.id} className="border-b border-line align-top last:border-0">
              <td className="px-5 py-2.5">
                <Link
                  to={`/p/${pid}/review?doc=${d.id}`}
                  className="flex items-start gap-2 font-medium text-navy-900 hover:underline"
                >
                  {d.filename.endsWith(".xlsx") ? (
                    <FileSpreadsheet className="mt-0.5 h-4 w-4 shrink-0 text-teal-700" />
                  ) : (
                    <FileText className="mt-0.5 h-4 w-4 shrink-0 text-navy-700" />
                  )}
                  <span className="break-all">{d.filename}</span>
                </Link>
                <div className="ml-6 mt-0.5 font-mono text-[10.5px] text-subtle" title={d.sha256}>
                  sha256 {d.sha256.slice(0, 12)}…
                </div>
                {d.profile.warnings.map((w) => (
                  <div key={w} className="ml-6 mt-1 flex items-start gap-1 text-[12px] text-amber-700">
                    <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0" /> {w}
                  </div>
                ))}
              </td>
              <td className="px-3 py-2.5">
                <select
                  aria-label={t("Document type for {file}", { file: d.filename })}
                  className="h-8 rounded-md border border-line-strong bg-surface px-2 text-[12.5px]"
                  value={d.doc_type}
                  onChange={(e) => onType(d.id, e.target.value)}
                >
                  {Object.entries(DOC_TYPES).map(([k, v]) => (
                    <option key={k} value={k}>
                      {t(v)}
                    </option>
                  ))}
                </select>
                {d.doc_type !== d.detected_type && (
                  <div className="mt-1 text-[11px] text-subtle">{t("set manually")}</div>
                )}
              </td>
              <td className="px-3 py-2.5">
                <div className="text-ink">{d.profile.institution ?? "–"}</div>
                {d.profile.jurisdiction && <Badge className="mt-1">{d.profile.jurisdiction}</Badge>}
              </td>
              <td className="num px-3 py-2.5 text-muted">
                {d.profile.period_start
                  ? `${d.profile.period_start} → ${d.profile.period_end}`
                  : (d.profile.as_of ?? "–")}
              </td>
              <td className="px-3 py-2.5">
                {d.profile.engines.includes("tesseract-ocr") ? (
                  <Badge tone="violet">
                    <ScanLine className="h-3 w-3" /> OCR
                  </Badge>
                ) : d.profile.engines.includes("openpyxl") ? (
                  <Badge>{t("Spreadsheet cells")}</Badge>
                ) : (
                  <Badge>{t("Digital text")}</Badge>
                )}
              </td>
              <td className="num px-3 py-2.5 text-right">{d.fact_count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
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
                <span className="num text-[12px] text-subtle">{chf(i.assets)}</span>
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
