/** CRM API client (/api/crm). Same demo identity headers as the rest of the app (lib/api.ts). */
import { ApiError, getRole } from "@/lib/api";
import { t } from "@/lib/i18n";

export type StageId = "lead" | "qualified" | "documents_received" | "cost_review" | "proposal_sent" | "won" | "lost";
export type Lifecycle = "prospect" | "client" | "lost";
export type Option = { id: string; label: string };

export interface Meta {
  stages: { id: StageId; label: string; open: boolean }[];
  lost_reasons: Option[];
  sources: Option[];
  kinds: Option[];
  activity_kinds: string[];
}

export interface Contact {
  id: number;
  name: string;
  kind: string;
  email: string;
  phone: string;
  domicile: string;
  source: string;
  owner: string;
  estimated_aum: string | null;
  currency: string;
  current_banks: string[];
  stage: StageId;
  stage_label: string;
  lifecycle: Lifecycle;
  lost_reason: string | null;
  next_action: string;
  next_action_due: string | null;
  notes: string;
  prospect: { id: number; code: string | null } | null;
  synthetic: boolean;
  created_at: string;
  updated_at: string;
}

export interface ContactDetail extends Contact {
  history: {
    from_stage: StageId | null;
    to_stage: StageId;
    to_label: string;
    at: string;
    user: string;
    note: string;
  }[];
  activities: { id: number; kind: string; summary: string; at: string; user: string }[];
}

export interface FunnelStage {
  stage: StageId;
  label: string;
  reached: number;
  current: number;
  share_of_total: string | null;
  conversion_from_previous: string | null;
  drop_off: number | null;
  median_days_in_stage: string | null;
  aum: Record<string, string>;
  aum_unknown: number;
}

export interface Funnel {
  total: number;
  open: number;
  won: number;
  lost: number;
  win_rate: string | null;
  overall_conversion: string | null;
  median_days_to_win: string | null;
  stages: FunnelStage[];
  lost_reasons: { reason: string; label: string; count: number; lost_after: Record<string, number> }[];
  by_source: {
    source: string;
    label: string;
    contacts: number;
    open: number;
    won: number;
    lost: number;
    win_rate: string | null;
  }[];
  pipeline_aum: Record<string, string>;
  pipeline_aum_unknown: number;
  owners: string[];
  synthetic: boolean;
}

export type ContactInput = Partial<
  Pick<
    Contact,
    | "name"
    | "kind"
    | "email"
    | "phone"
    | "domicile"
    | "source"
    | "owner"
    | "estimated_aum"
    | "currency"
    | "current_banks"
    | "next_action"
    | "next_action_due"
    | "notes"
  >
> & { stage?: StageId };

const USER_BY_ROLE: Record<string, string> = {
  analyst: "a.analyst",
  senior: "s.reviewer",
  relationship_manager: "r.manager",
};

async function req<T>(path: string, body?: unknown, method = body === undefined ? "GET" : "POST"): Promise<T> {
  const role = getRole();
  const res = await fetch(`/api/crm${path}`, {
    method,
    body: body === undefined ? undefined : JSON.stringify(body),
    headers: {
      "X-Tenant-Id": "demo-firm",
      "X-User": USER_BY_ROLE[role],
      "X-Role": role,
      ...(body === undefined ? {} : { "Content-Type": "application/json" }),
    },
  });
  if (!res.ok) {
    let msg = res.statusText;
    try {
      const j = await res.json();
      msg = typeof j.detail === "string" ? j.detail : (j.detail?.[0]?.msg ?? JSON.stringify(j.detail));
    } catch {
      /* not json */
    }
    throw new ApiError(res.status, msg);
  }
  return res.json() as Promise<T>;
}

const qs = (p: Record<string, string | undefined>) => {
  const s = new URLSearchParams(Object.entries(p).filter((e): e is [string, string] => !!e[1])).toString();
  return s ? `?${s}` : "";
};

export const crm = {
  meta: () => req<Meta>("/meta"),
  contacts: (f: { lifecycle?: string; q?: string; owner?: string } = {}) => req<Contact[]>(`/contacts${qs(f)}`),
  contact: (id: number) => req<ContactDetail>(`/contacts/${id}`),
  create: (b: ContactInput) => req<Contact>("/contacts", b),
  patch: (id: number, b: ContactInput) => req<ContactDetail>(`/contacts/${id}`, b, "PATCH"),
  move: (id: number, b: { to_stage: StageId; note?: string; lost_reason?: string }) =>
    req<ContactDetail>(`/contacts/${id}/stage`, b),
  addActivity: (id: number, b: { kind: string; summary: string }) => req(`/contacts/${id}/activities`, b),
  costReview: (id: number) => req<ContactDetail>(`/contacts/${id}/cost-review`, {}),
  funnel: (f: { since?: string; until?: string; owner?: string; source?: string }) => req<Funnel>(`/funnel${qs(f)}`),
  seed: () => req<{ contacts_added: number }>("/demo/seed", {}),
  byProspect: (pid: number) =>
    req<{ contact_id: number; name: string; stage: StageId; stage_label: string }>(`/by-prospect/${pid}`),
};

/** Ratio string from the API ("0.4250") → "42.5%"; null stays "Not determined" (never 0). */
export function ratioPct(v: string | null | undefined, d = 1): string {
  return v === null || v === undefined ? t("Not determined") : `${(Number(v) * 100).toFixed(d)}%`;
}

export const STAGE_TONE: Record<StageId, string> = {
  lead: "grey",
  qualified: "navy-soft",
  documents_received: "navy-soft",
  cost_review: "navy",
  proposal_sent: "violet",
  won: "green",
  lost: "red",
};

export const today = () => new Date().toISOString().slice(0, 10);
