import type { QueryClient } from "@tanstack/react-query";
import type { Analysis, DocumentRow, Fact, InternalView, ProposalConfig, ProspectRow, Taxonomy } from "./types";

export type Role = "analyst" | "senior" | "relationship_manager";

export const ROLE_LABEL: Record<Role, string> = {
  analyst: "Analyst",
  senior: "Senior reviewer",
  relationship_manager: "Relationship manager",
};

export interface Me {
  username: string;
  tenant: string;
  roles: Role[];
  admin: boolean;
  csrf_token: string;
}

// The session lives in an HttpOnly cookie the page cannot read. The CSRF token is kept in memory only
// and sent on every request; /api/auth/me hands it out again after a reload.
let csrf = "";
let allowedRoles: Role[] = ["analyst"];
let onSignedOut: () => void = () => {};

export function setSession(me: Me | null) {
  csrf = me?.csrf_token ?? "";
  allowedRoles = me?.roles.length ? me.roles : ["analyst"];
}

/** Called once by the app: what to do when the server says the session is gone. */
export function onUnauthorized(fn: () => void) {
  onSignedOut = fn;
}

/** Forget the session and every cached answer; the app falls back to the sign-in page. */
export function signedOut(qc: QueryClient) {
  setSession(null);
  qc.setQueryData(["me"], null);
  qc.removeQueries({ predicate: (q) => q.queryKey[0] !== "me" });
}

export function allowedRoleList(): Role[] {
  return allowedRoles;
}

export function getRole(): Role {
  try {
    const r = localStorage.getItem("pce.role") as Role | null;
    if (r && allowedRoles.includes(r)) return r;
  } catch {
    /* storage unavailable: default role */
  }
  return allowedRoles.includes("analyst") ? "analyst" : allowedRoles[0];
}

export function setRole(r: Role) {
  try {
    localStorage.setItem("pce.role", r);
  } catch {
    /* ignore */
  }
}

export function headers(extra?: Record<string, string>): Record<string, string> {
  return { "X-Role": getRole(), ...(csrf ? { "X-CSRF-Token": csrf } : {}), ...extra };
}

/** fetch with the session headers; a 401 sends the app back to the sign-in page. */
export async function authFetch(path: string, init?: RequestInit): Promise<Response> {
  const res = await fetch(path, { ...init, headers: headers(init?.headers as Record<string, string>) });
  if (res.status === 401) onSignedOut();
  return res;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await authFetch(path, init);
  if (!res.ok) {
    let msg = res.statusText;
    try {
      const j = await res.json();
      msg = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail);
    } catch {
      /* not json */
    }
    throw new ApiError(res.status, msg);
  }
  return res.json() as Promise<T>;
}

const json = (body: unknown, method = "POST"): RequestInit => ({
  method,
  body: JSON.stringify(body),
  headers: { "Content-Type": "application/json" },
});

export const auth = {
  me: () => req<Me>("/api/auth/me"),
  login: (username: string, password: string) => req<Me>("/api/auth/login", json({ username, password })),
  logout: () => req<{ ok: boolean }>("/api/auth/logout", { method: "POST" }),
};

export const api = {
  taxonomy: () => req<Taxonomy>("/api/taxonomy"),
  prospects: () => req<ProspectRow[]>("/api/prospects"),
  createProspect: (b: { code: string; label: string; domicile: string }) =>
    req<{ id: number }>("/api/prospects", json(b)),
  patchProspect: (id: number, b: { label?: string; domicile?: string }) =>
    req(`/api/prospects/${id}`, json(b, "PATCH")),
  seed: () => req<{ id: number; documents_added: number }>("/api/demo/seed", { method: "POST" }),
  documents: (id: number) => req<DocumentRow[]>(`/api/prospects/${id}/documents`),
  upload: (id: number, files: File[]) => {
    const fd = new FormData();
    for (const f of files) fd.append("files", f);
    return req<{ results: { filename: string; status: string; error?: string; doc_type?: string }[] }>(
      `/api/prospects/${id}/documents`,
      { method: "POST", body: fd },
    );
  },
  setDocType: (docId: number, doc_type: string) => req(`/api/documents/${docId}`, json({ doc_type }, "PATCH")),
  facts: (docId: number) => req<Fact[]>(`/api/documents/${docId}/facts`),
  sheet: (docId: number) =>
    req<{ sheets: { name: string; rows: (string | null)[][] }[] }>(`/api/documents/${docId}/sheet`),
  review: (factId: number, b: { action: string; value?: string; reason?: string }) =>
    req<Fact>(`/api/facts/${factId}/review`, json(b)),
  history: (factId: number) =>
    req<{ action: string; old: string | null; new: string | null; reason: string; user: string; at: string }[]>(
      `/api/facts/${factId}/history`,
    ),
  analysis: (id: number) => req<Analysis>(`/api/prospects/${id}/analysis`),
  internal: (id: number) => req<InternalView>(`/api/prospects/${id}/internal`),
  proposal: (id: number) =>
    req<{
      config: ProposalConfig;
      history: { version: number; user: string; at: string; summary: Record<string, string> }[];
    }>(`/api/prospects/${id}/proposal`),
  saveProposal: (id: number, cfg: Partial<ProposalConfig>) =>
    req<{ version: number }>(`/api/prospects/${id}/proposal`, json(cfg, "PUT")),
  setRequest: (id: number, key: string, status: string) =>
    req(`/api/prospects/${id}/requests/${encodeURIComponent(key)}`, json({ status }, "PATCH")),
  approve: (id: number, note: string) => req(`/api/prospects/${id}/approve`, json({ note })),
  audit: (id: number) =>
    req<{ at: string; user: string; action: string; detail: Record<string, unknown> }[]>(`/api/prospects/${id}/audit`),
  fileUrl: (docId: number) => `/api/documents/${docId}/file`,
  fetchFile: async (docId: number) => {
    const res = await authFetch(`/api/documents/${docId}/file`);
    if (!res.ok) throw new ApiError(res.status, "file not available");
    return res.arrayBuffer();
  },
  downloadReport: async (id: number, code: string) => {
    const res = await authFetch(`/api/prospects/${id}/report.pdf`);
    if (!res.ok) throw new ApiError(res.status, "report failed");
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `cost-review-${code}.pdf`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 2000);
  },
};
