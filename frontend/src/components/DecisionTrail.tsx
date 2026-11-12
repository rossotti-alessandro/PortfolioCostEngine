/** The decision trail of one value: read → automatic checks → person → where it is used. Steps come from lib/trail. */
import { api } from "@/lib/api";
import { cn } from "@/lib/format";
import { t } from "@/lib/i18n";
import { type StepKind, type Tone, trailSteps } from "@/lib/trail";
import type { EvidenceRef } from "@/lib/types";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Check, CircleDashed, CircleHelp, FileText, TriangleAlert, User, X } from "lucide-react";
import type { ReactNode } from "react";
import { Button } from "./ui";

const ICON: Record<StepKind, typeof Check> = {
  read: FileText,
  check: Check,
  flag: TriangleAlert,
  none: CircleHelp,
  person: User,
  pending: CircleDashed,
};

const TONE: Record<Tone, string> = {
  neutral: "bg-navy-100 text-navy-900",
  ok: "bg-green-100 text-green-700",
  warn: "bg-amber-50 text-amber-700",
  bad: "bg-red-100 text-red-700",
};

function when(at: string): string {
  const d = new Date(at);
  return Number.isNaN(d.getTime()) ? at : d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

function Step({
  icon: Icon,
  tone,
  title,
  detail,
}: { icon: typeof Check; tone: Tone; title: ReactNode; detail?: ReactNode }) {
  return (
    <li className="flex gap-3">
      <span className={cn("mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full", TONE[tone])}>
        <Icon className="h-3.5 w-3.5" aria-hidden />
      </span>
      <div className="min-w-0 text-[13px] leading-snug">
        <div className="font-medium text-ink">{title}</div>
        {detail && <div className="break-words text-[12px] text-muted">{detail}</div>}
      </div>
    </li>
  );
}

export function DecisionTrail({ e, usedIn }: { e: EvidenceRef; usedIn?: string[] }) {
  const qc = useQueryClient();
  const history = useQuery({ queryKey: ["history", e.fact_id], queryFn: () => api.history(e.fact_id) });
  const steps = trailSteps(e, history.data ?? []);
  const canAccept = e.status === "extracted" && history.isSuccess && history.data.length === 0;
  const accept = async () => {
    await api.review(e.fact_id, { action: "accept" });
    await Promise.all([
      qc.invalidateQueries({ queryKey: ["history", e.fact_id] }),
      qc.invalidateQueries({ queryKey: ["facts", e.document_id] }),
      qc.invalidateQueries({ queryKey: ["analysis"] }),
    ]);
  };
  return (
    <section aria-label={t("Decision trail")} className="space-y-2.5">
      <h4 className="text-[11.5px] font-semibold uppercase tracking-wider text-subtle">{t("Decision trail")}</h4>
      <ol className="space-y-2.5">
        {steps.map((s, i) => (
          <Step
            key={`${s.kind}-${i}`}
            icon={s.kind === "check" && s.tone === "bad" ? X : ICON[s.kind]}
            tone={s.tone}
            title={s.title}
            detail={[s.detail, s.at && when(s.at)].filter(Boolean).join(" · ") || undefined}
          />
        ))}
        {usedIn && usedIn.length > 0 && (
          <Step icon={ArrowRight} tone="neutral" title={t("Used in")} detail={usedIn.join(" › ")} />
        )}
      </ol>
      {canAccept && (
        <Button size="sm" onClick={accept}>
          <Check className="h-3.5 w-3.5" /> {t("Accept this value")}
        </Button>
      )}
    </section>
  );
}
