import { Button, Dialog, inputCls } from "@/components/ui";
import { cn } from "@/lib/format";
import { t } from "@/lib/i18n";
import { shrinkPhoto } from "@/lib/photos";
import { ArrowLeft, ArrowRight, Camera, ImagePlus, Trash2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";

type Page = { file: File; url: string };

const today = () => new Date().toISOString().slice(0, 10);

/** Scan a paper document with the phone: shoot pages one by one, check them, save as one PDF (SC-8.28).
 * Uses the phone's own camera app (`capture`), so the site never asks for camera permission. */
export function ScanDialog({
  open,
  onOpenChange,
  onSave,
}: {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  onSave: (pages: File[], name: string) => Promise<void>;
}) {
  const [pages, setPages] = useState<Page[]>([]);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const camera = useRef<HTMLInputElement>(null);
  const gallery = useRef<HTMLInputElement>(null);
  const urls = useRef<string[]>([]);

  const revoke = () => {
    for (const u of urls.current) URL.revokeObjectURL(u);
    urls.current = [];
  };
  // biome-ignore lint/correctness/useExhaustiveDependencies: revoke reads a ref; run on unmount only
  useEffect(() => revoke, []);
  const reset = () => {
    revoke();
    setPages([]);
    setName("");
    setError(null);
  };

  const add = async (files: File[]) => {
    setError(null);
    setBusy(true);
    const added: Page[] = [];
    for (const f of files) {
      try {
        const file = await shrinkPhoto(f);
        const url = URL.createObjectURL(file);
        urls.current.push(url);
        added.push({ file, url });
      } catch {
        setError(t("A photo could not be read. Use the camera, JPEG or PNG."));
      }
    }
    setPages((p) => [...p, ...added]);
    setBusy(false);
  };
  const move = (i: number, d: -1 | 1) =>
    setPages((p) => {
      const q = [...p];
      [q[i], q[i + d]] = [q[i + d], q[i]];
      return q;
    });

  const save = async () => {
    setBusy(true);
    setError(null);
    try {
      await onSave(
        pages.map((p) => p.file),
        name.trim() || t("Scan {date}", { date: today() }),
      );
      reset();
      onOpenChange(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const picker = (ref: React.RefObject<HTMLInputElement | null>, capture: boolean, label: string) => (
    <input
      ref={ref}
      type="file"
      accept="image/*"
      multiple={!capture}
      {...(capture ? { capture: "environment" } : {})}
      className="sr-only"
      aria-label={label}
      onChange={(e) => {
        const files = Array.from(e.target.files ?? []);
        e.target.value = "";
        if (files.length) add(files);
      }}
    />
  );

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        if (!o && !busy) reset();
        onOpenChange(o);
      }}
      title={t("Scan with camera")}
      description={t("Take one photo per page, flat and in good light. The pages are saved as one PDF and read here.")}
      wide
    >
      {picker(camera, true, t("Take a photo of a page"))}
      {picker(gallery, false, t("Add photos from the gallery"))}
      {pages.length > 0 && (
        <ol className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4" aria-label={t("Scanned pages")}>
          {pages.map((p, i) => (
            <li key={p.url} className="rounded-[var(--radius-control)] border border-line bg-paper p-1.5">
              <img
                src={p.url}
                alt={t("Page {n}", { n: i + 1 })}
                className="aspect-[3/4] w-full rounded-[2px] bg-surface object-contain"
              />
              <div className="mt-1 flex items-center justify-between gap-1">
                <span className="num text-[12px] text-muted">{t("Page {n}", { n: i + 1 })}</span>
                <span className="flex">
                  <Button
                    size="icon"
                    variant="ghost"
                    disabled={i === 0}
                    onClick={() => move(i, -1)}
                    aria-label={t("Move page {n} earlier", { n: i + 1 })}
                  >
                    <ArrowLeft className="h-4 w-4" />
                  </Button>
                  <Button
                    size="icon"
                    variant="ghost"
                    disabled={i === pages.length - 1}
                    onClick={() => move(i, 1)}
                    aria-label={t("Move page {n} later", { n: i + 1 })}
                  >
                    <ArrowRight className="h-4 w-4" />
                  </Button>
                  <Button
                    size="icon"
                    variant="ghost"
                    onClick={() => setPages((q) => q.filter((_, j) => j !== i))}
                    aria-label={t("Remove page {n}", { n: i + 1 })}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </span>
              </div>
            </li>
          ))}
        </ol>
      )}
      <div className={cn("flex flex-wrap gap-2", !pages.length && "justify-center py-6")}>
        <Button
          size="lg"
          variant={pages.length ? "outline" : "primary"}
          onClick={() => camera.current?.click()}
          loading={busy && !pages.length}
        >
          <Camera className="h-5 w-5" /> {pages.length ? t("Add a page") : t("Take a photo of a page")}
        </Button>
        <Button size="lg" variant="ghost" onClick={() => gallery.current?.click()}>
          <ImagePlus className="h-5 w-5" /> {t("From gallery")}
        </Button>
      </div>
      {error && (
        <p role="alert" className="mt-3 text-[13px] text-red-700">
          {error}
        </p>
      )}
      {pages.length > 0 && (
        <div className="mt-4 flex flex-col gap-2 border-t border-line pt-4 sm:flex-row sm:items-end">
          <label className="flex-1 text-[13px] text-muted">
            {t("Document name (optional)")}
            <input
              className={cn(inputCls, "mt-1 w-full")}
              value={name}
              maxLength={120}
              placeholder={t("Scan {date}", { date: today() })}
              onChange={(e) => setName(e.target.value)}
            />
          </label>
          <Button size="lg" onClick={save} loading={busy} disabled={busy}>
            {t("Save as one document ({n} pages)", { n: pages.length })}
          </Button>
        </div>
      )}
    </Dialog>
  );
}
