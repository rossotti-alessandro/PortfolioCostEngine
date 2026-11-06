import { Badge, Button, Dialog, ErrorBox, Field, inputCls } from "@/components/ui";
import { cn } from "@/lib/format";
import { t } from "@/lib/i18n";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BarChart3, KanbanSquare, List, Plus } from "lucide-react";
import { type ReactNode, useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { type ContactInput, STAGE_TONE, type StageId, crm } from "./api";

export const useMeta = () =>
  useQuery({ queryKey: ["crm", "meta"], queryFn: crm.meta, staleTime: Number.POSITIVE_INFINITY });

export function StageBadge({ stage, label }: { stage: StageId; label: string }) {
  return <Badge tone={STAGE_TONE[stage]}>{label}</Badge>;
}

export function SyntheticBanner() {
  return (
    <div className="border-b border-amber-700/20 bg-amber-50 px-4 py-1 text-center text-[12.5px] text-amber-700">
      {t("SYNTHETIC demo data. Contacts, banks and amounts are invented.")}
    </div>
  );
}

const tabCls = ({ isActive }: { isActive: boolean }) =>
  cn(
    "inline-flex items-center gap-1.5 border-b-2 px-1 pb-2.5 text-[13.5px] font-medium",
    isActive ? "border-navy-900 text-navy-900" : "border-transparent text-muted hover:text-ink",
  );

/** Header shared by the CRM pages: title, tabs and the one primary action. */
export function CrmHeader({ actions, synthetic }: { actions?: ReactNode; synthetic?: boolean }) {
  return (
    <>
      {synthetic && <SyntheticBanner />}
      <div className="border-b border-line bg-surface">
        <div className="mx-auto max-w-[1440px] px-4 pt-5 sm:px-8">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <h1 className="text-xl font-semibold text-navy-900">{t("Clients & pipeline")}</h1>
              <p className="mt-1 max-w-2xl text-[13.5px] text-muted">
                {t("Track every relationship from first contact to signed mandate, and see where prospects drop out.")}
              </p>
            </div>
            {actions && <div className="flex flex-wrap gap-2 pb-1">{actions}</div>}
          </div>
          <nav aria-label={t("Pipeline views")} className="mt-4 flex gap-5">
            <NavLink to="/crm" end className={tabCls}>
              <KanbanSquare className="h-4 w-4" /> {t("Board")}
            </NavLink>
            <NavLink to="/crm/list" className={tabCls}>
              <List className="h-4 w-4" /> {t("Contacts")}
            </NavLink>
            <NavLink to="/crm/funnel" className={tabCls}>
              <BarChart3 className="h-4 w-4" /> {t("Funnel")}
            </NavLink>
          </nav>
        </div>
      </div>
    </>
  );
}

export function NewContactButton() {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button onClick={() => setOpen(true)}>
        <Plus className="h-4 w-4" /> {t("New contact")}
      </Button>
      <NewContactDialog open={open} onOpenChange={setOpen} />
    </>
  );
}

function NewContactDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (o: boolean) => void }) {
  const nav = useNavigate();
  const qc = useQueryClient();
  const { data: meta } = useMeta();
  const [f, setF] = useState<ContactInput>({
    name: "",
    kind: "family",
    source: "referral",
    domicile: "CH",
    stage: "lead",
  });
  const [banks, setBanks] = useState("");
  const set = (k: keyof ContactInput) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value });
  const m = useMutation({
    mutationFn: () =>
      crm.create({
        ...f,
        estimated_aum: f.estimated_aum ? f.estimated_aum.replace(/['\s,]/g, "") : null,
        current_banks: banks
          .split(",")
          .map((b) => b.trim())
          .filter(Boolean),
      }),
    onSuccess: (c) => {
      qc.invalidateQueries({ queryKey: ["crm"] });
      onOpenChange(false);
      nav(`/crm/c/${c.id}`);
    },
  });
  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      title={t("New contact")}
      description={t("A lead or prospect. It becomes a client when you mark it as won.")}
    >
      <form
        className="grid gap-3 sm:grid-cols-2"
        onSubmit={(e) => {
          e.preventDefault();
          m.mutate();
        }}
      >
        <div className="sm:col-span-2">
          <Field label={t("Name")}>
            <input className={inputCls} value={f.name} onChange={set("name")} required maxLength={200} />
          </Field>
        </div>
        <Field label={t("Type")}>
          <select className={inputCls} value={f.kind} onChange={set("kind")}>
            {meta?.kinds.map((k) => (
              <option key={k.id} value={k.id}>
                {k.label}
              </option>
            ))}
          </select>
        </Field>
        <Field label={t("Source")}>
          <select className={inputCls} value={f.source} onChange={set("source")}>
            {meta?.sources.map((k) => (
              <option key={k.id} value={k.id}>
                {k.label}
              </option>
            ))}
          </select>
        </Field>
        <Field label={t("Estimated assets (CHF)")} hint={t("Leave empty if unknown. It is not counted as zero.")}>
          <input
            className={inputCls}
            inputMode="decimal"
            value={f.estimated_aum ?? ""}
            onChange={set("estimated_aum")}
          />
        </Field>
        <Field label={t("Tax domicile")}>
          <select className={inputCls} value={f.domicile} onChange={set("domicile")}>
            {["CH", "IT", "DE", "FR", "GB", "US"].map((d) => (
              <option key={d}>{d}</option>
            ))}
          </select>
        </Field>
        <div className="sm:col-span-2">
          <Field label={t("Current banks")} hint={t("Comma separated.")}>
            <input className={inputCls} value={banks} onChange={(e) => setBanks(e.target.value)} />
          </Field>
        </div>
        <Field label={t("Starting stage")}>
          <select className={inputCls} value={f.stage} onChange={set("stage")}>
            {meta?.stages
              .filter((s) => s.open)
              .map((s) => (
                <option key={s.id} value={s.id}>
                  {s.label}
                </option>
              ))}
          </select>
        </Field>
        <Field label={t("Email")}>
          <input className={inputCls} type="email" value={f.email ?? ""} onChange={set("email")} />
        </Field>
        {m.error && (
          <div className="sm:col-span-2">
            <ErrorBox error={m.error} />
          </div>
        )}
        <div className="flex justify-end gap-2 pt-2 sm:col-span-2">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {t("Cancel")}
          </Button>
          <Button type="submit" loading={m.isPending}>
            {t("Create contact")}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}

/** Move a contact; asks for a reason when it is lost. Used on the board and the contact page. */
export function MoveDialog({ contactId, to, onClose }: { contactId: number; to: StageId | null; onClose: () => void }) {
  const qc = useQueryClient();
  const { data: meta } = useMeta();
  const [note, setNote] = useState("");
  const [reason, setReason] = useState("");
  const m = useMutation({
    mutationFn: () => crm.move(contactId, { to_stage: to as StageId, note, lost_reason: reason || undefined }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["crm"] });
      setNote("");
      setReason("");
      onClose();
    },
  });
  const label = meta?.stages.find((s) => s.id === to)?.label ?? to ?? "";
  return (
    <Dialog open={to !== null} onOpenChange={(o) => !o && onClose()} title={t("Move to {stage}", { stage: label })}>
      <form
        className="space-y-3"
        onSubmit={(e) => {
          e.preventDefault();
          m.mutate();
        }}
      >
        {to === "lost" && (
          <Field label={t("Why was it lost?")}>
            <select className={inputCls} value={reason} onChange={(e) => setReason(e.target.value)} required>
              <option value="">{t("Choose a reason")}</option>
              {meta?.lost_reasons.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.label}
                </option>
              ))}
            </select>
          </Field>
        )}
        <Field label={t("Note (optional)")}>
          <textarea
            className={cn(inputCls, "h-20 py-2")}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            maxLength={1000}
          />
        </Field>
        {m.error && <ErrorBox error={m.error} />}
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>
            {t("Cancel")}
          </Button>
          <Button type="submit" variant={to === "lost" ? "danger" : "primary"} loading={m.isPending}>
            {t("Move to {stage}", { stage: label })}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
