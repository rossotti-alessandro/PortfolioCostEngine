/** A readable crop of the source page around one value: the cited row boxed, the context above and below dimmed.
 *  It is the first thing the evidence panel shows, so the analyst reads the original text at real size. */
import { t } from "@/lib/i18n";
import type * as pdfjs from "pdfjs-dist";
import { useEffect, useRef, useState } from "react";
import { usePdf } from "./EvidenceViewer";
import { Spinner } from "./ui";

const PAD_X = 12; // points of margin left and right of the box
const CONTEXT_Y = 30; // points of context above and below the row
const MAX_SCALE = 3;

interface Region {
  scale: number;
  x0: number;
  y0: number;
  w: number;
  h: number;
}

/** The page region to show for a bbox, scaled to fit `avail` px wide. Exported for tests. */
export function cropRegion(bbox: number[], pageW: number, pageH: number, avail: number): Region {
  const [bx0, by0, bx1, by1] = bbox;
  const x0 = Math.max(0, bx0 - PAD_X);
  const x1 = Math.min(pageW, bx1 + PAD_X);
  const y0 = Math.max(0, by0 - CONTEXT_Y);
  const y1 = Math.min(pageH, by1 + CONTEXT_Y);
  const scale = Math.min(MAX_SCALE, avail / Math.max(1, x1 - x0));
  return { scale, x0, y0, w: (x1 - x0) * scale, h: (y1 - y0) * scale };
}

export function SourceCrop({ docId, page, bbox, tag }: { docId: number; page: number; bbox: number[]; tag?: string }) {
  const pdf = usePdf(docId);
  const wrap = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const [r, setR] = useState<Region | null>(null);

  useEffect(() => {
    if (!pdf || !wrap.current || !canvas.current) return;
    let task: pdfjs.RenderTask | null = null;
    let cancelled = false;
    pdf.getPage(Math.min(page, pdf.numPages)).then((p) => {
      if (cancelled || !wrap.current || !canvas.current) return;
      const base = p.getViewport({ scale: 1 });
      const reg = cropRegion(bbox, base.width, base.height, wrap.current.clientWidth - 2);
      const vp = p.getViewport({ scale: reg.scale });
      const dpr = window.devicePixelRatio || 1;
      const c = canvas.current;
      c.width = Math.floor(vp.width * dpr);
      c.height = Math.floor(vp.height * dpr);
      c.style.width = `${vp.width}px`;
      c.style.height = `${vp.height}px`;
      task = p.render({
        canvasContext: c.getContext("2d")!,
        viewport: vp,
        transform: dpr !== 1 ? [dpr, 0, 0, dpr, 0, 0] : undefined,
      });
      task.promise.then(() => !cancelled && setR(reg)).catch(() => {});
    });
    return () => {
      cancelled = true;
      task?.cancel();
    };
  }, [pdf, page, bbox]);

  const [bx0, by0, bx1, by1] = bbox;
  return (
    <div ref={wrap} className="w-full">
      <div
        className="relative overflow-hidden rounded-md border border-line bg-white"
        style={{ height: r ? r.h : 96, width: r ? r.w : "100%" }}
        data-testid="source-crop"
      >
        {!r && <Spinner label={t("Locating source")} />}
        <canvas
          ref={canvas}
          className="absolute block"
          style={r ? { left: -r.x0 * r.scale, top: -r.y0 * r.scale } : { visibility: "hidden" }}
          aria-hidden
        />
        {r && (
          <>
            {/* Dim everything but the cited row so the eye lands on it. */}
            <div className="absolute inset-x-0 top-0 bg-paper/70" style={{ height: (by0 - r.y0) * r.scale - 3 }} />
            <div className="absolute inset-x-0 bottom-0 bg-paper/70" style={{ top: (by1 - r.y0) * r.scale + 3 }} />
            <div
              className="evidence-box pointer-events-none"
              data-active="true"
              role="img"
              aria-label={t("Where the value is written")}
              style={{
                left: (bx0 - r.x0) * r.scale - 3,
                top: (by0 - r.y0) * r.scale - 3,
                width: (bx1 - bx0) * r.scale + 6,
                height: (by1 - by0) * r.scale + 6,
              }}
            />
            {tag && (
              <span className="num absolute right-1.5 top-1.5 rounded bg-teal-700 px-1.5 py-0.5 text-[11px] font-semibold text-white">
                {tag}
              </span>
            )}
          </>
        )}
      </div>
    </div>
  );
}
