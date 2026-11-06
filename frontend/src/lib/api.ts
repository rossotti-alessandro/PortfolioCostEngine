import type { Analysis, DocumentRow, Fact, InternalView, ProposalConfig, ProspectRow, Taxonomy } from "./types";

export type Role = "analyst" | "senior" | "relationship_manager";

export const ROLE_LABEL: Record<Role, string> = {
  analyst: "Analyst",
  senior: "Senior reviewer",
  relationship_manager: "Relationship manager",
};

const USER_BY_ROLE: Record<Role, string> = {
  analyst: "a.analyst",
  senior: "s.reviewer",
  relationship_manager: "r.manager",
};

export function getRole(): Role {
  try {
    const r = localStorage.getItem("pce.role") as Role | null;
    if (r && r in ROLE_LABEL) return r;
  } catch {
    /* storage unavailable: default role */
  }
  return "analyst";
}

export function setRole(r: Role) {
  try {
    localStorage.setItem("pce.role", r);
  } catch {
    /* ignore */
  }
}

function headers(extra?: Record<string, string>): Record<string, string> {
  const role = getRole();
  return { "X-Tenant-Id": "demo-firm", "X-User": USER_BY_ROLE[role], "X-Role": role, ...extra };
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, { ...init, headers: headers(init?.headers as Record<string, string>) });
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
    const res = await fetch(`/api/documents/${docId}/file`, { headers: headers() });
    if (!res.ok) throw new ApiError(res.status, "file not available");
    return res.arrayBuffer();
  },
  downloadReport: async (id: number, code: string) => {
    const res = await fetch(`/api/prospects/${id}/report.pdf`, { headers: headers() });
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
