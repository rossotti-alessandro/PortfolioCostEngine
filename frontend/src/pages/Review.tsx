import { Button, Card, Dialog, Field, Spinner, inputCls } from "@/components/ui";
import { api } from "@/lib/api";
import { cn } from "@/lib/format";
import { t } from "@/lib/i18n";
import type { Fact } from "@/lib/types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { DocumentStage } from "./review/DocumentStage";
import { ValueRail } from "./review/ValueRail";
import { QUEUE, type QueueKey } from "./review/shared";

/**
 * Check values. From 1280px the source page takes two thirds of the width and
 * the value rail takes the remaining third. Below that they stack: the document
 * first, then the value being checked. The file list is a switcher in the stage,
 * never a third column.
 */
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
  const [prefill, setPrefill] = useState<string | null>(null); // the expert's value, offered in the dialog
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

  if (docs.isLoading) return <Spinner />;
  if (!docs.data?.length) return <Card className="p-8 text-center text-muted">{t("Upload documents first.")}</Card>;
  const isSheet = !!doc?.filename.toLowerCase().endsWith(".xlsx");

  return (
    <div className="grid min-h-0 flex-1 gap-3 xl:grid-cols-[minmax(0,2fr)_minmax(17.5rem,1fr)] xl:grid-rows-[minmax(0,1fr)] xl:overflow-hidden">
      <DocumentStage
        docs={docs.data}
        doc={doc}
        docId={docId}
        onSelectDoc={(id) => {
          setSp({ doc: String(id) });
          setActiveId(null);
        }}
        facts={facts.data}
        activeId={activeId}
        activePage={active?.evidence.page ?? undefined}
        isSheet={isSheet}
        onSelectFact={select}
      />
      <ValueRail
        all={facts.data ?? []}
        ordered={ordered}
        loading={facts.isLoading}
        shownQueue={shownQueue}
        onQueue={setQueue}
        active={active}
        activeId={activeId}
        onSelect={setActiveId}
        docId={docId}
        isSheet={isSheet}
        busy={review.isPending}
        error={review.error}
        onAccept={() => active && review.mutate({ id: active.id, action: "accept" })}
        onCorrect={() => setEditing("correct")}
        onReject={() => setEditing("reject")}
        onUndo={() => active && review.mutate({ id: active.id, action: "reset", reason: "reset" })}
        doc={doc}
        pid={pid}
        onUseExpert={(value) => {
          setPrefill(value);
          setEditing("correct");
        }}
      />
      {active && (
        <EditDialog
          mode={editing}
          fact={active}
          initial={prefill}
          busy={review.isPending}
          onClose={() => {
            setEditing(null);
            setPrefill(null);
          }}
          onSubmit={(value, reason) => review.mutate({ id: active.id, action: editing!, value, reason })}
        />
      )}
    </div>
  );
}

function EditDialog({
  mode,
  fact,
  initial,
  busy,
  onClose,
  onSubmit,
}: {
  mode: "correct" | "reject" | null;
  fact: Fact;
  initial: string | null;
  busy: boolean;
  onClose: () => void;
  onSubmit: (value: string | undefined, reason: string) => void;
}) {
  const [value, setValue] = useState(initial ?? fact.value ?? "");
  const [reason, setReason] = useState("");
  // biome-ignore lint/correctness/useExhaustiveDependencies: reset the form whenever the dialog opens for another action
  useEffect(() => {
    setValue(initial ?? fact.value ?? "");
    setReason("");
  }, [fact, mode, initial]);
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
