import { Badge, Button, Card, Empty, ErrorBox, Kpi, Spinner, inputCls } from "@/components/ui";
import { chf, cn, moneyOr } from "@/lib/format";
import { t } from "@/lib/i18n";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRightLeft, CalendarClock, ChevronRight, FlaskConical, GripVertical, Search, Users } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { type Contact, type StageId, crm, ratioPct, today } from "./api";
import { CrmHeader, MoveDialog, NewContactButton, StageBadge, useMeta } from "./common";

function SeedButton({ variant = "outline" }: { variant?: "outline" | "accent" }) {
  const qc = useQueryClient();
  const m = useMutation({ mutationFn: crm.seed, onSuccess: () => qc.invalidateQueries({ queryKey: ["crm"] }) });
  return (
    <Button variant={variant} onClick={() => m.mutate()} loading={m.isPending}>
      <FlaskConical className="h-4 w-4" /> {t("Load synthetic CRM")}
    </Button>
  );
}

function useContacts(filter: { lifecycle?: string; q?: string } = {}) {
  return useQuery({ queryKey: ["crm", "contacts", filter], queryFn: () => crm.contacts(filter) });
}

function Due({ c }: { c: Contact }) {
  if (!c.next_action || c.lifecycle !== "prospect") return null;
  const overdue = c.next_action_due !== null && c.next_action_due < today();
  return (
    <div className="mt-2 flex items-start gap-1.5 text-[12px] text-muted">
      <CalendarClock className="mt-px h-3.5 w-3.5 shrink-0" aria-hidden />
      <span>
        {t(c.next_action)}
        {c.next_action_due && (
          <span className="num">
            {" · "}
            {overdue && <span className="font-medium text-amber-700">{t("overdue")} </span>}
            {c.next_action_due}
          </span>
        )}
      </span>
    </div>
  );
}

/** Below 1024 px a kanban needs sideways scrolling; narrow screens get a stage list instead. */
function useWide() {
  const q = "(min-width: 1024px)";
  const [wide, setWide] = useState(() => typeof window === "undefined" || window.matchMedia(q).matches);
  useEffect(() => {
    const m = window.matchMedia(q);
    const on = () => setWide(m.matches);
    m.addEventListener("change", on);
    return () => m.removeEventListener("change", on);
  }, []);
  return wide;
}

/** "Move to" as a small button that opens the native picker: one tap on a phone, keyboard on a desktop. */
function MoveSelect({
  c,
  stages,
  onMove,
}: { c: Contact; stages: { id: StageId; label: string }[]; onMove: (to: StageId) => void }) {
  return (
    <label className="relative inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-[var(--radius-control)] text-muted hover:bg-paper focus-within:ring-2 focus-within:ring-teal-600/30">
      <ArrowRightLeft className="h-4 w-4" aria-hidden />
      <select
        aria-label={t("Move {name} to", { name: c.name })}
        className="absolute inset-0 cursor-pointer opacity-0"
        value=""
        onChange={(e) => e.target.value && onMove(e.target.value as StageId)}
      >
        <option value="">{t("Move to…")}</option>
        {stages
          .filter((x) => x.id !== c.stage)
          .map((x) => (
            <option key={x.id} value={x.id}>
              {t(x.label)}
            </option>
          ))}
      </select>
    </label>
  );
}

/** Next actions that are due today or late, oldest first: the first thing an adviser needs each morning. */
function Today({ contacts, shown }: { contacts: Contact[]; shown: number }) {
  const [all, setAll] = useState(false);
  const now = today();
  const due = contacts
    .filter((c) => c.lifecycle === "prospect" && c.next_action && c.next_action_due && c.next_action_due <= now)
    .sort((a, b) => (a.next_action_due ?? "").localeCompare(b.next_action_due ?? ""));
  return (
    <Card className="mb-5">
      <div className="flex items-center justify-between border-b border-line px-4 py-3 sm:px-5">
        <h2 className="text-[14px] font-semibold text-navy-900">{t("Needs you today")}</h2>
        <span className="num text-[12.5px] text-muted">{due.length}</span>
      </div>
      {!due.length ? (
        <p className="px-4 py-3 text-[13px] text-muted sm:px-5">{t("Nothing due. Every next action is on time.")}</p>
      ) : (
        <ul aria-label={t("Needs you today")}>
          {(all ? due : due.slice(0, shown)).map((c) => (
            <li key={c.id} className="border-b border-line last:border-0">
              <Link
                to={`/crm/c/${c.id}`}
                className="flex min-h-[52px] items-center gap-3 px-4 py-2.5 hover:bg-paper/60 sm:px-5"
              >
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-[13.5px] font-medium text-navy-900">{c.name}</span>
                  <span className="block truncate text-[12.5px] text-muted">{t(c.next_action)}</span>
                </span>
                <span
                  className={cn(
                    "num shrink-0 text-[12px]",
                    (c.next_action_due ?? "") < now ? "font-medium text-amber-700" : "text-muted",
                  )}
                >
                  {(c.next_action_due ?? "") < now ? `${t("overdue")} ${c.next_action_due}` : t("today")}
                </span>
                <ChevronRight className="h-4 w-4 shrink-0 text-subtle" aria-hidden />
              </Link>
            </li>
          ))}
        </ul>
      )}
      {due.length > shown && (
        <button
          type="button"
          className="w-full border-t border-line px-4 py-2.5 text-left text-[13px] font-medium text-teal-700 hover:bg-paper/60 sm:px-5"
          onClick={() => setAll(!all)}
        >
          {all ? t("Show fewer") : t("Show all {n}", { n: due.length })}
        </button>
      )}
    </Card>
  );
}

/** Phone and tablet: stage chips, then full-width rows. Same data and moves as the board. */
function StageList({
  contacts,
  stages,
  onMove,
}: {
  contacts: Contact[];
  stages: { id: StageId; label: string; open: boolean }[];
  onMove: (c: Contact, to: StageId) => void;
}) {
  const [stage, setStage] = useState<StageId | "open">("open");
  const shown = contacts.filter((c) => (stage === "open" ? c.lifecycle === "prospect" : c.stage === stage));
  const chips: [StageId | "open", string, number][] = [
    ["open", t("All open"), contacts.filter((c) => c.lifecycle === "prospect").length],
    ...stages.map((s): [StageId, string, number] => [
      s.id,
      t(s.label),
      contacts.filter((c) => c.stage === s.id).length,
    ]),
  ];
  return (
    <>
      <div role="tablist" aria-label={t("Stages")} className="no-scrollbar -mx-4 mb-3 flex gap-2 overflow-x-auto px-4">
        {chips.map(([id, label, n]) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={stage === id}
            onClick={() => setStage(id)}
            className={cn(
              "inline-flex h-9 shrink-0 items-center gap-1.5 rounded-full border px-3 text-[13px] font-medium",
              stage === id ? "border-navy-900 bg-navy-900 text-white" : "border-line-strong bg-surface text-ink",
            )}
          >
            {label} <span className={cn("num", stage === id ? "text-white/80" : "text-muted")}>{n}</span>
          </button>
        ))}
      </div>
      <Card>
        {!shown.length ? (
          <p className="px-4 py-4 text-[13px] text-muted">{t("No contacts in this stage.")}</p>
        ) : (
          <ul aria-label={t("Contacts")}>
            {shown.map((c) => (
              <li key={c.id} className="flex items-start gap-2 border-b border-line px-4 py-3 last:border-0">
                <Link to={`/crm/c/${c.id}`} className="min-w-0 flex-1">
                  <span className="flex items-center gap-2">
                    <span className="truncate text-[14px] font-medium text-navy-900">{c.name}</span>
                    {stage === "open" && <StageBadge stage={c.stage} label={t(c.stage_label)} />}
                  </span>
                  <span className="num mt-0.5 block text-[12.5px] text-muted">
                    {c.estimated_aum ? chf(c.estimated_aum) : t("AUM not estimated")} · {c.owner}
                  </span>
                  <Due c={c} />
                </Link>
                <MoveSelect c={c} stages={stages} onMove={(to) => onMove(c, to)} />
              </li>
            ))}
          </ul>
        )}
      </Card>
    </>
  );
}

function Shell({ children, synthetic }: { children: React.ReactNode; synthetic?: boolean }) {
  // The synthetic seed lives in the empty state only: next to "New contact" it looked like a real action.
  return (
    <div>
      <CrmHeader synthetic={synthetic} actions={<NewContactButton />} />
      <div className="mx-auto max-w-[1440px] px-4 py-6 sm:px-8">{children}</div>
    </div>
  );
}

const useFunnelAll = () => useQuery({ queryKey: ["crm", "funnel", {}], queryFn: () => crm.funnel({}) });

function Headline() {
  const { data: f } = useFunnelAll();
  if (!f || f.total === 0) return null;
  return (
    <div className="mb-5 grid grid-cols-2 gap-3 lg:grid-cols-4">
      {/* Phone: pipeline assets first and full width (the long CHF figure), win rate on the Funnel tab. */}
      <div className="col-span-2 grid lg:order-2 lg:col-span-1">
        <Kpi
          label={t("Pipeline assets")}
          value={moneyOr(f.pipeline_aum.CHF, f.pipeline_aum_unknown ? t("Not estimated") : "–")}
          sub={
            f.pipeline_aum_unknown
              ? t("{n} without an estimate (not counted as zero)", { n: f.pipeline_aum_unknown })
              : t("All open contacts estimated")
          }
        />
      </div>
      <div className="grid lg:order-1">
        <Kpi label={t("Open prospects")} value={f.open} sub={t("{n} contacts in total", { n: f.total })} />
      </div>
      <div className="grid lg:order-3">
        <Kpi label={t("Clients won")} value={f.won} tone="teal" sub={t("{n} lost", { n: f.lost })} />
      </div>
      <div className="hidden sm:grid lg:order-4">
        <Kpi
          label={t("Win rate")}
          value={ratioPct(f.win_rate)}
          sub={t("Won ÷ (won + lost)")}
          help={t("Share of closed opportunities that became clients")}
        />
      </div>
    </div>
  );
}

/** Kanban board: one column per open stage, then won and lost. Drag a card, or use its "Move to" menu. */
export default function BoardPage() {
  const { data: meta } = useMeta();
  const { data, isLoading, error } = useContacts();
  const { data: funnel } = useFunnelAll();
  const nav = useNavigate();
  const [move, setMove] = useState<{ id: number; to: StageId } | null>(null);
  const [drag, setDrag] = useState<number | null>(null);
  const [over, setOver] = useState<StageId | null>(null);
  const [said, setSaid] = useState(""); // announced to screen readers after a move
  const qc = useQueryClient();
  const quick = useMutation({
    mutationFn: (v: { id: number; to: StageId }) => crm.move(v.id, { to_stage: v.to }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["crm"] }),
  });
  const request = (id: number, to: StageId) => (to === "lost" ? setMove({ id, to }) : quick.mutate({ id, to }));
  const moveAndSay = (c: Contact, to: StageId) => {
    request(c.id, to);
    if (to !== "lost")
      setSaid(
        t("{name} moved to {stage}", { name: c.name, stage: t(meta?.stages.find((x) => x.id === to)?.label ?? to) }),
      );
  };
  const wide = useWide();

  return (
    <Shell synthetic={data?.some((c) => c.synthetic)}>
      {isLoading || !meta ? (
        <Spinner />
      ) : error ? (
        <ErrorBox error={error} />
      ) : !data?.length ? (
        <Card>
          <Empty icon={<Users className="h-8 w-8" />} title={t("No contacts yet")}>
            {t("Add your first lead, or load a synthetic book of 41 contacts to explore the pipeline and the funnel.")}
            <div className="mt-4 flex justify-center gap-2">
              <SeedButton variant="accent" />
            </div>
          </Empty>
        </Card>
      ) : (
        <>
          <Today contacts={data} shown={wide ? 3 : 5} />
          <Headline />
          {quick.error && <ErrorBox error={quick.error} />}
          {!wide ? (
            <StageList contacts={data} stages={meta.stages} onMove={(c, to) => moveAndSay(c, to)} />
          ) : (
            <div className="flex gap-3 overflow-x-auto pb-3" aria-label={t("Pipeline board")}>
              {meta.stages.map((s) => {
                const cards = data.filter((c) => c.stage === s.id);
                // Column totals come from the API (the frontend formats, it never re-computes totals).
                const fs = funnel?.stages.find((x) => x.stage === s.id);
                return (
                  <section
                    key={s.id}
                    aria-label={t(s.label)}
                    data-stage={s.id}
                    onDragOver={(e) => {
                      if (drag === null) return;
                      e.preventDefault();
                      e.dataTransfer.dropEffect = "move";
                      setOver(s.id);
                    }}
                    onDragLeave={(e) => {
                      // leaving for a child of the same column is not leaving the column
                      if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setOver(null);
                    }}
                    onDrop={(e) => {
                      e.preventDefault();
                      const c = data.find((x) => x.id === drag);
                      if (c && c.stage !== s.id) {
                        request(c.id, s.id);
                        if (s.id !== "lost") setSaid(t("{name} moved to {stage}", { name: c.name, stage: t(s.label) }));
                      }
                      setDrag(null);
                      setOver(null);
                    }}
                    className={cn(
                      "flex w-[260px] shrink-0 flex-col rounded-[var(--radius-card)] border bg-surface-muted/60 transition-colors",
                      over === s.id && drag !== null && data.find((x) => x.id === drag)?.stage !== s.id
                        ? "border-2 border-dashed border-teal-600 bg-teal-50"
                        : "border-line",
                    )}
                  >
                    <header className="border-b border-line px-3 py-2.5">
                      <div className="flex items-center justify-between">
                        <h2 className="text-[13px] font-semibold text-navy-900">{t(s.label)}</h2>
                        <span className="num rounded-full bg-surface px-2 text-[12px] text-muted ring-1 ring-line">
                          {cards.length}
                        </span>
                      </div>
                      {s.open && fs && (
                        <div className="num mt-0.5 text-[11.5px] text-subtle">
                          {moneyOr(fs.aum.CHF, fs.aum_unknown > 0 ? t("Not estimated") : "–")}
                          {fs.aum_unknown > 0 && ` + ${t("{n} not estimated", { n: fs.aum_unknown })}`}
                        </div>
                      )}
                    </header>
                    <ul className={cn("flex-1 space-y-2 p-2", !s.open && "max-h-[520px] overflow-y-auto")}>
                      {cards.map((c) => (
                        <li
                          key={c.id}
                          draggable
                          onDragStart={(e) => {
                            e.dataTransfer.effectAllowed = "move";
                            e.dataTransfer.setData("text/plain", String(c.id)); // Firefox starts a drag only with data
                            setDrag(c.id);
                          }}
                          onDragEnd={() => {
                            setDrag(null);
                            setOver(null);
                          }}
                          className={cn(
                            "group relative cursor-grab select-none rounded-[var(--radius-control)] border border-line bg-surface p-3 pl-6 hover:border-line-strong active:cursor-grabbing",
                            drag === c.id && "opacity-40",
                          )}
                        >
                          <GripVertical
                            className="absolute left-1.5 top-3.5 h-3.5 w-3.5 text-subtle/60 group-hover:text-subtle"
                            aria-hidden
                          />
                          <div className="flex items-start gap-1">
                            <Link
                              to={`/crm/c/${c.id}`}
                              className="min-w-0 flex-1 text-[13.5px] font-medium leading-snug text-navy-900 hover:underline"
                            >
                              {c.name}
                            </Link>
                            <span className="-mr-1.5 -mt-1.5">
                              <MoveSelect c={c} stages={meta.stages} onMove={(to) => moveAndSay(c, to)} />
                            </span>
                          </div>
                          <div className="num mt-1 flex flex-wrap items-center gap-x-2 text-[12px] text-muted">
                            <span>{c.estimated_aum ? chf(c.estimated_aum) : t("AUM not estimated")}</span>
                            <span>· {c.owner}</span>
                          </div>
                          {c.lost_reason && (
                            <div className="mt-1 text-[12px] text-red-700">
                              {t(meta.lost_reasons.find((r) => r.id === c.lost_reason)?.label ?? "")}
                            </div>
                          )}
                          {c.prospect && (
                            <Link to={`/p/${c.prospect.id}/costs`} className="mt-2 inline-block">
                              <Badge tone="teal">
                                {t("Cost review")} {c.prospect.code}
                              </Badge>
                            </Link>
                          )}
                          <Due c={c} />
                        </li>
                      ))}
                    </ul>
                  </section>
                );
              })}
            </div>
          )}
          <p className="sr-only" aria-live="polite">
            {said}
          </p>
          <p className="mt-2 text-[12px] text-subtle">
            {wide && t("Drag a card to another column, or use its menu. Click a name to open the contact.")}{" "}
            <button type="button" className="underline" onClick={() => nav("/crm/funnel")}>
              {t("See the conversion funnel")}
            </button>
          </p>
        </>
      )}
      {move && <MoveDialog contactId={move.id} to={move.to} onClose={() => setMove(null)} />}
    </Shell>
  );
}

/** Table of all contacts, filterable by lifecycle (prospects, clients, lost) and name. */
export function ContactsPage() {
  const [lifecycle, setLifecycle] = useState("");
  const [q, setQ] = useState("");
  const { data, isLoading, error } = useContacts({ lifecycle: lifecycle || undefined, q: q || undefined });
  const nav = useNavigate();
  const tabs = [
    ["", t("All")],
    ["prospect", t("Prospects")],
    ["client", t("Clients")],
    ["lost", t("Lost")],
  ];
  return (
    <Shell synthetic={data?.some((c) => c.synthetic)}>
      <Card>
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-5 py-3">
          <div className="flex gap-1" role="tablist" aria-label={t("Lifecycle")}>
            {tabs.map(([v, l]) => (
              <button
                key={v}
                type="button"
                role="tab"
                aria-selected={lifecycle === v}
                onClick={() => setLifecycle(v)}
                className={cn(
                  "rounded-md px-3 py-1.5 text-[13px] font-medium",
                  lifecycle === v ? "bg-navy-100 text-navy-900" : "text-muted hover:bg-paper",
                )}
              >
                {l}
              </button>
            ))}
          </div>
          <label className="relative w-full max-w-xs">
            <span className="sr-only">{t("Search by name")}</span>
            <Search className="pointer-events-none absolute left-2.5 top-2.5 h-4 w-4 text-subtle" />
            <input
              className={cn(inputCls, "pl-8")}
              placeholder={t("Search by name")}
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
          </label>
        </div>
        {isLoading ? (
          <Spinner />
        ) : error ? (
          <ErrorBox error={error} />
        ) : !data?.length ? (
          <Empty title={t("No contacts match")}>{t("Change the filter or add a new contact.")}</Empty>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-[13.5px]">
              <thead>
                <tr className="border-b border-line text-left text-[12px] uppercase tracking-wide text-subtle">
                  <th className="px-5 py-2.5 font-medium">{t("Name")}</th>
                  <th className="px-3 py-2.5 font-medium">{t("Stage")}</th>
                  <th className="px-3 py-2.5 text-right font-medium">{t("Estimated assets")}</th>
                  <th className="px-3 py-2.5 font-medium">{t("Current banks")}</th>
                  <th className="px-3 py-2.5 font-medium">{t("Owner")}</th>
                  <th className="px-3 py-2.5 font-medium">{t("Next action")}</th>
                  <th className="px-5 py-2.5 font-medium">{t("Cost review")}</th>
                </tr>
              </thead>
              <tbody>
                {data.map((c) => (
                  <tr
                    key={c.id}
                    tabIndex={0}
                    className="cursor-pointer border-b border-line last:border-0 hover:bg-paper/60"
                    onClick={() => nav(`/crm/c/${c.id}`)}
                    onKeyDown={(e) => e.key === "Enter" && nav(`/crm/c/${c.id}`)}
                  >
                    <td className="px-5 py-3">
                      <div className="font-medium text-navy-900">{c.name}</div>
                      <div className="text-[12px] text-subtle">
                        {c.kind} · {c.domicile}
                      </div>
                    </td>
                    <td className="px-3 py-3">
                      <StageBadge stage={c.stage} label={t(c.stage_label)} />
                    </td>
                    <td className="num px-3 py-3 text-right">
                      {c.estimated_aum ? (
                        chf(c.estimated_aum)
                      ) : (
                        <span className="text-subtle">{t("Not estimated")}</span>
                      )}
                    </td>
                    <td className="px-3 py-3 text-[12.5px] text-muted">{c.current_banks.join(", ") || "–"}</td>
                    <td className="px-3 py-3 text-muted">{c.owner}</td>
                    <td className="px-3 py-3 text-[12.5px] text-muted">
                      {c.lifecycle === "prospect" ? t(c.next_action) || "–" : "–"}
                      {c.lifecycle === "prospect" && c.next_action_due && (
                        <div className={cn("num", c.next_action_due < today() && "text-amber-700")}>
                          {c.next_action_due}
                        </div>
                      )}
                    </td>
                    <td className="px-5 py-3">{c.prospect ? <Badge tone="teal">{c.prospect.code}</Badge> : "–"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </Shell>
  );
}
