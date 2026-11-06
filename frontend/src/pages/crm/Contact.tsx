import { Badge, Button, Card, CardHeader, ErrorBox, Field, Spinner, inputCls } from "@/components/ui";
import { chf, cn } from "@/lib/format";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Check, ChevronRight, FileSearch, MessageSquarePlus, Trophy, XCircle } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { type ContactDetail, type StageId, crm, today } from "./api";
import { MoveDialog, StageBadge, SyntheticBanner, useMeta } from "./common";

const OPEN: StageId[] = ["lead", "qualified", "documents_received", "cost_review", "proposal_sent"];

/** Horizontal stage tracker: done / current / to do, plus Won and Lost actions. */
function StageTrack({ c, onMove }: { c: ContactDetail; onMove: (s: StageId) => void }) {
  const { data: meta } = useMeta();
  const reached = new Set(c.history.map((h) => h.to_stage));
  const cur = OPEN.indexOf(c.stage);
  const far = Math.max(...c.history.map((h) => OPEN.indexOf(h.to_stage)), c.stage === "won" ? OPEN.length : -1);
  return (
    <Card className="p-4">
      <ol className="grid grid-cols-2 gap-2 sm:grid-cols-5" aria-label="Pipeline stages">
        {OPEN.map((s, i) => {
          const label = meta?.stages.find((x) => x.id === s)?.label ?? s;
          const state = c.stage === s ? "current" : i <= far || reached.has(s) ? "done" : "todo";
          return (
            <li key={s}>
              <button
                type="button"
                disabled={c.stage === s}
                onClick={() => onMove(s)}
                aria-current={state === "current" ? "step" : undefined}
                title={state === "current" ? "Current stage" : `Move to ${label}`}
                className={cn(
                  "flex w-full items-center gap-2 rounded-md border px-2.5 py-2 text-left text-[12.5px] font-medium",
                  state === "current" && "border-navy-900 bg-navy-900 text-white",
                  state === "done" && "border-teal-700/30 bg-teal-50 text-teal-700 hover:border-teal-700",
                  state === "todo" && "border-line bg-surface text-muted hover:border-line-strong hover:text-ink",
                )}
              >
                <span
                  className={cn(
                    "flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[11px]",
                    state === "current"
                      ? "bg-white text-navy-900"
                      : state === "done"
                        ? "bg-teal-700 text-white"
                        : "ring-1 ring-line-strong",
                  )}
                >
                  {state === "done" ? <Check className="h-3 w-3" /> : i + 1}
                </span>
                {label}
              </button>
            </li>
          );
        })}
      </ol>
      <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-line pt-3">
        <span className="mr-auto text-[13px] text-muted">
          {c.stage === "won" ? (
            <span className="font-medium text-green-700">Client since {c.updated_at.slice(0, 10)}</span>
          ) : c.stage === "lost" ? (
            <span className="font-medium text-red-700">
              Lost: {meta?.lost_reasons.find((r) => r.id === c.lost_reason)?.label ?? c.lost_reason}
            </span>
          ) : (
            <>
              Step {cur + 1} of {OPEN.length}
            </>
          )}
        </span>
        {c.stage !== "won" && (
          <Button variant="accent" size="sm" onClick={() => onMove("won")}>
            <Trophy className="h-4 w-4" /> Mark as won
          </Button>
        )}
        {c.stage !== "lost" && c.stage !== "won" && (
          <Button variant="danger" size="sm" onClick={() => onMove("lost")}>
            <XCircle className="h-4 w-4" /> Mark as lost
          </Button>
        )}
        {(c.stage === "lost" || c.stage === "won") && (
          <Button variant="outline" size="sm" onClick={() => onMove("qualified")}>
            Reopen
          </Button>
        )}
      </div>
    </Card>
  );
}

function CostReviewCard({ c }: { c: ContactDetail }) {
  const qc = useQueryClient();
  const m = useMutation({
    mutationFn: () => crm.costReview(c.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["crm"] }),
  });
  return (
    <Card>
      <CardHeader title="Cost review" subtitle="The evidence-based analysis of what the portfolio costs today." />
      <div className="px-5 py-4 text-[13.5px]">
        {c.prospect ? (
          <Link
            to={`/p/${c.prospect.id}/costs`}
            className="inline-flex items-center gap-1.5 font-medium text-teal-700 hover:underline"
          >
            <FileSearch className="h-4 w-4" /> Open cost review {c.prospect.code}
            <ArrowRight className="h-4 w-4" />
          </Link>
        ) : (
          <>
            <p className="mb-3 text-muted">No cost review yet. Start one to upload this contact's bank documents.</p>
            <Button variant="outline" size="sm" onClick={() => m.mutate()} loading={m.isPending}>
              <FileSearch className="h-4 w-4" /> Start cost review
            </Button>
            {m.error && <ErrorBox error={m.error} />}
          </>
        )}
      </div>
    </Card>
  );
}

function NextAction({ c }: { c: ContactDetail }) {
  const qc = useQueryClient();
  const [text, setText] = useState(c.next_action);
  const [due, setDue] = useState(c.next_action_due ?? "");
  const m = useMutation({
    mutationFn: () => crm.patch(c.id, { next_action: text, next_action_due: due || "" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["crm"] }),
  });
  const dirty = text !== c.next_action || due !== (c.next_action_due ?? "");
  return (
    <Card>
      <CardHeader title="Next action" />
      <form
        className="space-y-3 px-5 py-4"
        onSubmit={(e) => {
          e.preventDefault();
          m.mutate();
        }}
      >
        <Field label="What">
          <input className={inputCls} value={text} onChange={(e) => setText(e.target.value)} maxLength={500} />
        </Field>
        <Field label="Due">
          <input className={inputCls} type="date" value={due} onChange={(e) => setDue(e.target.value)} />
        </Field>
        {c.next_action_due && c.next_action_due < today() && <Badge tone="amber">Overdue</Badge>}
        {m.error && <ErrorBox error={m.error} />}
        {dirty && (
          <Button type="submit" size="sm" loading={m.isPending}>
            Save next action
          </Button>
        )}
      </form>
    </Card>
  );
}

function Timeline({ c }: { c: ContactDetail }) {
  const qc = useQueryClient();
  const { data: meta } = useMeta();
  const [kind, setKind] = useState("note");
  const [summary, setSummary] = useState("");
  const m = useMutation({
    mutationFn: () => crm.addActivity(c.id, { kind, summary }),
    onSuccess: () => {
      setSummary("");
      qc.invalidateQueries({ queryKey: ["crm"] });
    },
  });
  const items = [
    ...c.history.map((h) => ({
      at: h.at,
      key: `s-${h.at}-${h.to_stage}`,
      title: h.from_stage ? `Moved to ${h.to_label}` : `Created as ${h.to_label}`,
      body: h.note,
      user: h.user,
      stage: true,
    })),
    ...c.activities.map((a) => ({
      at: a.at,
      key: `a-${a.id}`,
      title: a.kind,
      body: a.summary,
      user: a.user,
      stage: false,
    })),
  ].sort((a, b) => b.at.localeCompare(a.at));
  return (
    <Card>
      <CardHeader title="Activity and stage history" subtitle="Every stage change is recorded with who and when." />
      <form
        className="flex flex-wrap gap-2 border-b border-line px-5 py-3"
        onSubmit={(e) => {
          e.preventDefault();
          m.mutate();
        }}
      >
        <label>
          <span className="sr-only">Activity type</span>
          <select className={cn(inputCls, "w-28")} value={kind} onChange={(e) => setKind(e.target.value)}>
            {meta?.activity_kinds.map((k) => (
              <option key={k} value={k}>
                {k}
              </option>
            ))}
          </select>
        </label>
        <label className="min-w-[200px] flex-1">
          <span className="sr-only">Activity summary</span>
          <input
            className={inputCls}
            placeholder="Log a call, meeting or note"
            value={summary}
            onChange={(e) => setSummary(e.target.value)}
            maxLength={2000}
            required
          />
        </label>
        <Button type="submit" variant="outline" loading={m.isPending}>
          <MessageSquarePlus className="h-4 w-4" /> Add
        </Button>
      </form>
      <ol className="divide-y divide-line">
        {items.map((it) => (
          <li key={it.key} className="flex gap-3 px-5 py-3">
            <span
              className={cn("mt-1.5 h-2 w-2 shrink-0 rounded-full", it.stage ? "bg-navy-900" : "bg-teal-700")}
              aria-hidden
            />
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <span className="text-[13.5px] font-medium text-ink first-letter:uppercase">{it.title}</span>
                <span className="num text-[12px] text-subtle">
                  {it.at.slice(0, 16).replace("T", " ")} · {it.user}
                </span>
              </div>
              {it.body && <p className="mt-0.5 text-[13px] text-muted">{it.body}</p>}
            </div>
          </li>
        ))}
      </ol>
    </Card>
  );
}

export default function ContactPage() {
  const id = Number(useParams().id);
  const { data: c, isLoading, error } = useQuery({ queryKey: ["crm", "contact", id], queryFn: () => crm.contact(id) });
  const { data: meta } = useMeta();
  const [to, setTo] = useState<StageId | null>(null);
  if (isLoading) return <Spinner />;
  if (error || !c) return <ErrorBox error={error ?? "Contact not found"} />;
  const label = (list: { id: string; label: string }[] | undefined, v: string) =>
    list?.find((x) => x.id === v)?.label ?? v;
  return (
    <div>
      {c.synthetic && <SyntheticBanner />}
      <div className="border-b border-line bg-surface">
        <div className="mx-auto max-w-[1200px] px-4 py-4 sm:px-8">
          <div className="flex items-center gap-1.5 text-[12px] text-subtle">
            <Link to="/crm" className="hover:text-ink">
              Clients & pipeline
            </Link>
            <ChevronRight className="h-3 w-3" />
            <span>{c.lifecycle === "client" ? "Client" : c.lifecycle === "lost" ? "Lost" : "Prospect"}</span>
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-3">
            <h1 className="text-xl font-semibold text-navy-900">{c.name}</h1>
            <StageBadge stage={c.stage} label={c.stage_label} />
          </div>
          <div className="mt-1 flex flex-wrap gap-x-3 text-[13px] text-muted">
            <span className="num font-medium text-ink">
              {c.estimated_aum ? chf(c.estimated_aum) : "Assets not estimated"}
            </span>
            <span>{label(meta?.kinds, c.kind)}</span>
            <span>Domicile {c.domicile}</span>
            <span>Source: {label(meta?.sources, c.source)}</span>
            <span>Owner: {c.owner}</span>
          </div>
        </div>
      </div>
      <div className="mx-auto max-w-[1200px] space-y-4 px-4 py-6 sm:px-8">
        <StageTrack c={c} onMove={setTo} />
        <div className="grid gap-4 lg:grid-cols-[1fr_340px]">
          <Timeline c={c} />
          <div className="space-y-4">
            <NextAction key={`${c.id}-${c.updated_at}`} c={c} />
            <CostReviewCard c={c} />
            <Card>
              <CardHeader title="Details" />
              <dl className="grid grid-cols-[110px_1fr] gap-y-2 px-5 py-4 text-[13px]">
                <dt className="text-subtle">Current banks</dt>
                <dd>{c.current_banks.join(", ") || "–"}</dd>
                <dt className="text-subtle">Email</dt>
                <dd className="break-all">{c.email || "–"}</dd>
                <dt className="text-subtle">Phone</dt>
                <dd>{c.phone || "–"}</dd>
                <dt className="text-subtle">Created</dt>
                <dd className="num">{c.created_at.slice(0, 10)}</dd>
              </dl>
            </Card>
          </div>
        </div>
      </div>
      <MoveDialog contactId={c.id} to={to} onClose={() => setTo(null)} />
    </div>
  );
}
