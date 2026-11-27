/** Expert agent in review (SC-5.24): ask it about a document's doubtful values, show what it proposes.
 *  A proposal is a suggestion with the line it was read from. Only the analyst changes a value. */

import { Button, ErrorBox } from "@/components/ui";
import { api } from "@/lib/api";
import { t } from "@/lib/i18n";
import type { DocumentRow, ExpertProposal, Fact } from "@/lib/types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Sparkles } from "lucide-react";
import { useEffect } from "react";

const ACTION: Record<ExpertProposal["action"], string> = {
  confirm: "The expert agrees with this value",
  correct: "The expert reads a different value",
  new: "The expert found this fee",
  not_a_fee: "The expert thinks this is not a cost",
  abstain: "The expert could not tell",
};

export const proposalOf = (f: Fact): ExpertProposal | null => (f.extra?.expert as ExpertProposal) ?? null;

/** Button and progress for one document. Polls while the expert works, then refreshes the values. */
export function AskExpert({ doc, pid, open }: { doc: DocumentRow; pid: number; open: number }) {
  const qc = useQueryClient();
  const health = useQuery({ queryKey: ["health"], queryFn: api.health, staleTime: 300_000 });
  const st = doc.profile.expert;
  const working = st?.status === "queued" || st?.status === "running";
  const ask = useMutation({
    mutationFn: () => api.askExpert(doc.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["documents", pid] }),
  });
  useEffect(() => {
    if (!working) return;
    const id = setInterval(() => {
      qc.invalidateQueries({ queryKey: ["documents", pid] });
      qc.invalidateQueries({ queryKey: ["facts", doc.id] });
    }, 4000);
    return () => clearInterval(id);
  }, [working, qc, pid, doc.id]);
  // no model set up on this installation: no button (rule: no inert controls)
  if (!health.data?.expert || !doc.filename.toLowerCase().endsWith(".pdf") || (!open && !working)) return null;
  return (
    <div className="mt-2 text-[12px]">
      <Button size="sm" variant="outline" onClick={() => ask.mutate()} loading={ask.isPending} disabled={working}>
        <Sparkles className="h-3.5 w-3.5" /> {t("Ask the expert")}
      </Button>
      <span className="ml-2 text-muted">
        {working
          ? t("Checking {done} of {total}…", { done: st.done, total: st.total })
          : st?.status === "failed"
            ? t("The expert stopped ({error}). Values are unchanged.", { error: st.error ?? "" })
            : st?.status === "done"
              ? t("Done. Its suggestions are shown on each value.")
              : t("Checks the values that need you, and looks for missed fees.")}
      </span>
      {ask.error ? <ErrorBox error={ask.error} /> : null}
    </div>
  );
}

/** The proposal on the value being checked, with the line it was read from. */
export function ExpertSuggestion({ fact, onUse }: { fact: Fact; onUse: (value: string) => void }) {
  const p = proposalOf(fact);
  if (!p || p.dropped) return null;
  const differs = p.action === "correct" && p.value !== null && p.value !== fact.value;
  return (
    <div className="mt-2 rounded-[var(--radius-control)] border border-line bg-surface px-3 py-2 text-[12px]">
      <div className="flex items-center gap-1.5 font-medium text-navy-900">
        <Sparkles className="h-3.5 w-3.5 shrink-0" /> {t(ACTION[p.action])}
        {p.value !== null && (
          <span className="num ml-1">
            {p.value}
            {p.unit === "%" ? " %" : p.currency ? ` ${p.currency}` : ""}
          </span>
        )}
      </div>
      {p.quote && <div className="mt-1 line-clamp-2 font-mono text-[11px] text-muted">“{p.quote}”</div>}
      {p.reason && <div className="mt-0.5 text-subtle">{p.reason}</div>}
      {differs && (
        <Button size="sm" variant="outline" className="mt-1.5" onClick={() => onUse(p.value!)}>
          {t("Use this value")}
        </Button>
      )}
      <div className="mt-1 text-[11px] text-subtle">
        {t("A suggestion only: check it on the page before you decide.")}
      </div>
    </div>
  );
}
