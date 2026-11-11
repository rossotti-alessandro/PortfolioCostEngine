import { api } from "@/lib/api";
import { cn } from "@/lib/format";
import { t } from "@/lib/i18n";
import type { Fact } from "@/lib/types";
import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, ZoomIn, ZoomOut } from "lucide-react";
import * as pdfjs from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import { useEffect, useMemo, useRef, useState } from "react";
import { Button, Spinner } from "./ui";

pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;

/** Renders the original PDF page with pdf.js and overlays every extracted value's rectangle.
 *  Coordinates are PDF points with a top-left origin, scaled to the rendered viewport. */
export function PdfEvidence({
  docId,
  facts,
  activeId,
  onSelect,
  page: pageProp,
  compact,
}: {
  docId: number;
  facts: Fact[];
  activeId?: number | null;
  onSelect?: (f: Fact) => void;
  page?: number;
  compact?: boolean;
}) {
  const file = useQuery({
    queryKey: ["file", docId],
    queryFn: () => api.fetchFile(docId),
    staleTime: Number.POSITIVE_INFINITY,
  });
  const [pdf, setPdf] = useState<pdfjs.PDFDocumentProxy | null>(null);
  const [page, setPage] = useState(pageProp ?? 1);
  const [zoom, setZoom] = useState(1);
  const [size, setSize] = useState<{ w: number; h: number; scale: number } | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const activeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!file.data) return;
    let cancelled = false;
    pdfjs.getDocument({ data: file.data.slice(0), isEvalSupported: false }).promise.then((d) => {
      if (!cancelled) setPdf(d);
    });
    return () => {
      cancelled = true;
    };
  }, [file.data]);

  useEffect(() => {
    if (pageProp) setPage(pageProp);
  }, [pageProp]);

  useEffect(() => {
    if (!pdf || !canvasRef.current || !wrapRef.current) return;
    let task: pdfjs.RenderTask | null = null;
    let cancelled = false;
    pdf.getPage(Math.min(page, pdf.numPages)).then((p) => {
      if (cancelled || !canvasRef.current || !wrapRef.current) return;
      const base = p.getViewport({ scale: 1 });
      const avail = Math.max(320, wrapRef.current.clientWidth - 2);
      const scale = (avail / base.width) * zoom;
      const vp = p.getViewport({ scale });
      const dpr = window.devicePixelRatio || 1;
      const c = canvasRef.current;
      c.width = Math.floor(vp.width * dpr);
      c.height = Math.floor(vp.height * dpr);
      c.style.width = `${vp.width}px`;
      c.style.height = `${vp.height}px`;
      const ctx = c.getContext("2d")!;
      task = p.render({ canvasContext: ctx, viewport: vp, transform: dpr !== 1 ? [dpr, 0, 0, dpr, 0, 0] : undefined });
      task.promise.then(() => !cancelled && setSize({ w: vp.width, h: vp.height, scale })).catch(() => {});
    });
    return () => {
      cancelled = true;
      task?.cancel();
    };
  }, [pdf, page, zoom]);

  // biome-ignore lint/correctness/useExhaustiveDependencies: re-scroll when the selection or the rendered size changes
  useEffect(() => {
    activeRef.current?.scrollIntoView({ block: "center", behavior: "smooth" });
  }, [activeId, size]);

  const onPage = useMemo(() => facts.filter((f) => f.evidence.page === page && f.evidence.bbox), [facts, page]);
  const n = pdf?.numPages ?? 1;

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex items-center justify-between gap-2 border-b border-line bg-paper/70 px-3 py-1.5">
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            aria-label={t("Previous page")}
            disabled={page <= 1}
            onClick={() => setPage(page - 1)}
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="num text-[12.5px] text-muted">{t("Page {page} / {n}", { page, n })}</span>
          <Button
            variant="ghost"
            size="icon"
            aria-label={t("Next page")}
            disabled={page >= n}
            onClick={() => setPage(page + 1)}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
        {!compact && (
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="icon"
              aria-label={t("Zoom out")}
              onClick={() => setZoom(Math.max(0.6, zoom - 0.2))}
            >
              <ZoomOut className="h-4 w-4" />
            </Button>
            <span className="num w-10 text-center text-[12px] text-muted">{Math.round(zoom * 100)}%</span>
            <Button
              variant="ghost"
              size="icon"
              aria-label={t("Zoom in")}
              onClick={() => setZoom(Math.min(2.4, zoom + 0.2))}
            >
              <ZoomIn className="h-4 w-4" />
            </Button>
          </div>
        )}
      </div>
      <div ref={wrapRef} className="relative min-h-0 flex-1 overflow-auto bg-[#e9e7e1] p-3">
        {!pdf && <Spinner label={t("Opening document")} />}
        <div className="relative mx-auto w-fit shadow-[0_2px_10px_rgb(0_0_0/0.12)]">
          <canvas ref={canvasRef} className="block bg-white" />
          {size &&
            onPage.map((f) => {
              const [x0, y0, x1, y1] = f.evidence.bbox!;
              const s = size.scale;
              const active = f.id === activeId;
              return (
                <button
                  type="button"
                  key={f.id}
                  ref={active ? activeRef : undefined}
                  aria-label={`${f.label}: ${f.value ?? t("no value")}`}
                  title={`${f.label} → ${f.value ?? t("unknown")}`}
                  className="evidence-box"
                  data-active={active}
                  data-status={f.status}
                  onClick={() => onSelect?.(f)}
                  style={{ left: x0 * s - 3, top: y0 * s - 2, width: (x1 - x0) * s + 6, height: (y1 - y0) * s + 4 }}
                />
              );
            })}
        </div>
      </div>
    </div>
  );
}

/** Spreadsheet evidence: shows the sheet as a grid and highlights the cited cell and its row. */
export function SheetEvidence({
  docId,
  facts,
  activeId,
  onSelect,
}: { docId: number; facts: Fact[]; activeId?: number | null; onSelect?: (f: Fact) => void }) {
  const { data } = useQuery({
    queryKey: ["sheet", docId],
    queryFn: () => api.sheet(docId),
    staleTime: Number.POSITIVE_INFINITY,
  });
  const active = facts.find((f) => f.id === activeId);
  const activeRef = useRef<HTMLTableCellElement>(null);
  // biome-ignore lint/correctness/useExhaustiveDependencies: re-scroll when the selection changes
  useEffect(() => {
    activeRef.current?.scrollIntoView({ block: "center", inline: "center", behavior: "smooth" });
  }, [activeId]);
  if (!data) return <Spinner label={t("Opening spreadsheet")} />;
  const sheet = data.sheets.find((s) => s.name === active?.evidence.sheet) ?? data.sheets[0];
  const cellOf = (r: number, c: number) => `${String.fromCharCode(65 + c)}${r + 1}`;
  const byCell = new Map(facts.filter((f) => f.evidence.sheet === sheet.name).map((f) => [f.evidence.cell, f]));
  const activeRow = active?.evidence.cell ? Number(active.evidence.cell.replace(/[A-Z]+/, "")) - 1 : -1;
  const width = Math.max(...sheet.rows.map((r) => r.length), 1);
  return (
    <div className="h-full overflow-auto bg-[#e9e7e1] p-3">
      <div className="mb-2 text-[12px] text-muted">{t("Sheet “{name}”", { name: sheet.name })}</div>
      <table className="num border-collapse bg-white text-[12px] shadow-[0_2px_10px_rgb(0_0_0/0.12)]">
        <thead>
          <tr>
            <th className="border border-line bg-paper px-1.5 text-subtle" />
            {Array.from({ length: width }, (_, c) => (
              <th key={c} className="border border-line bg-paper px-2 py-0.5 font-medium text-subtle">
                {String.fromCharCode(65 + c)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sheet.rows.map((row, r) => (
            <tr key={r} className={cn(r === activeRow && "bg-amber-50")}>
              <td className="border border-line bg-paper px-1.5 text-right text-subtle">{r + 1}</td>
              {Array.from({ length: width }, (_, c) => {
                const ref = cellOf(r, c);
                const f = byCell.get(ref);
                const isActive = f && f.id === activeId;
                return (
                  <td
                    key={c}
                    ref={isActive ? activeRef : undefined}
                    onClick={() => f && onSelect?.(f)}
                    onKeyDown={(e) => e.key === "Enter" && f && onSelect?.(f)}
                    tabIndex={f ? 0 : undefined}
                    className={cn(
                      "max-w-[260px] truncate whitespace-nowrap border border-line px-2 py-1",
                      f && "cursor-pointer bg-teal-50 outline outline-1 -outline-offset-1 outline-teal-600/50",
                      isActive && "bg-amber-100 outline-2 outline-[#d99a00]",
                    )}
                  >
                    {row[c] ?? ""}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
