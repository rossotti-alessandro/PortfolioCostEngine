import { ROLE_LABEL, type Role, api, getRole, setRole } from "@/lib/api";
import { PRODUCT } from "@/lib/brand";
import { chf, cn } from "@/lib/format";
import { setLang, t, useLang } from "@/lib/i18n";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { BookOpen, Check, ChevronRight, FolderOpen, Lock, ShieldCheck, Workflow } from "lucide-react";
import { type ReactNode, useState } from "react";
import { Link, NavLink, Outlet, useMatch, useParams } from "react-router-dom";
import { Badge } from "./ui";

export function Brand() {
  return (
    <Link to="/prospects" className="flex items-center gap-2.5 px-2">
      <img src="/favicon.svg" alt="" className="h-7 w-7" />
      <div className="leading-tight">
        <div className="text-[15px] font-semibold tracking-tight text-navy-900">{PRODUCT.name}</div>
        <div className="text-[11px] text-subtle">{t(PRODUCT.tagline)}</div>
      </div>
    </Link>
  );
}

function LangSwitch() {
  const lang = useLang();
  return (
    <fieldset
      className="mb-3 flex rounded-md border border-line bg-surface p-0.5 text-[12px]"
      aria-label={t("Language")}
    >
      {(["en", "it"] as const).map((l) => (
        <button
          key={l}
          type="button"
          aria-pressed={lang === l}
          onClick={() => setLang(l)}
          className={cn(
            "flex-1 rounded px-2 py-1 font-medium",
            lang === l ? "bg-navy-900 text-white" : "text-muted hover:text-ink",
          )}
        >
          {l === "en" ? "English" : "Italiano"}
        </button>
      ))}
    </fieldset>
  );
}

function RoleSwitch() {
  const qc = useQueryClient();
  const [role, setR] = useState<Role>(getRole());
  return (
    <label className="block text-[11.5px] text-subtle">
      {t("Demo role")}
      <select
        aria-label={t("Demo role")}
        value={role}
        onChange={(e) => {
          const r = e.target.value as Role;
          setRole(r);
          setR(r);
          qc.invalidateQueries();
        }}
        className="mt-1 h-8 w-full rounded-md border border-line-strong bg-surface px-2 text-[13px] text-ink focus:outline-none focus:ring-2 focus:ring-teal-600/20"
      >
        {(Object.keys(ROLE_LABEL) as Role[]).map((r) => (
          <option key={r} value={r}>
            {t(ROLE_LABEL[r])}
          </option>
        ))}
      </select>
    </label>
  );
}

const STEPS = [
  { to: "documents", label: "Documents" },
  { to: "review", label: "Review evidence" },
  { to: "costs", label: "Current costs" },
  { to: "compare", label: "Compare" },
  { to: "report", label: "Client report" },
];

const navCls = ({ isActive }: { isActive: boolean }) =>
  cn(
    "flex items-center gap-2.5 rounded-md px-2.5 py-1.5 text-[13.5px] font-medium",
    isActive ? "bg-navy-100 text-navy-900" : "text-muted hover:bg-paper hover:text-ink",
  );

function ProspectNav({ pid }: { pid: number }) {
  const { data } = useQuery({ queryKey: ["analysis", pid], queryFn: () => api.analysis(pid) });
  const { data: docs } = useQuery({ queryKey: ["documents", pid], queryFn: () => api.documents(pid) });
  const done: Record<string, boolean> = {
    documents: (docs?.length ?? 0) > 0,
    review: !!data && data.review.facts > 0 && data.review.reviewed + data.review.rejected >= data.review.facts,
    costs: !!data && data.current.is_complete,
    compare: false,
    report: !!data?.approval?.valid,
  };
  return (
    <div className="mt-5">
      <div className="px-2.5 text-[11px] font-semibold uppercase tracking-wider text-subtle">{t("Prospect")}</div>
      <div className="mt-1 truncate px-2.5 text-[13px] font-medium text-ink" title={data?.prospect.label}>
        {data?.prospect.label ?? "…"}
      </div>
      <nav aria-label={t("Review workflow")} className="mt-2 space-y-0.5">
        {STEPS.map((s, i) => (
          <NavLink key={s.to} to={`/p/${pid}/${s.to}`} className={navCls}>
            {({ isActive }) => (
              <>
                <span
                  className={cn(
                    "flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[11px]",
                    done[s.to]
                      ? "bg-teal-700 text-white"
                      : isActive
                        ? "bg-navy-900 text-white"
                        : "bg-surface text-muted ring-1 ring-line-strong",
                  )}
                >
                  {done[s.to] ? <Check className="h-3 w-3" /> : i + 1}
                </span>
                {t(s.label)}
              </>
            )}
          </NavLink>
        ))}
        <NavLink to={`/p/${pid}/internal`} className={navCls}>
          <Lock className="ml-0.5 h-4 w-4" /> {t("Internal economics")}
        </NavLink>
      </nav>
    </div>
  );
}

/** Left navigation (240px) per DESIGN_SYSTEM.md §3; collapses to a top block on small screens. */
export function AppShell() {
  const m = useMatch("/p/:id/*");
  const pid = m ? Number(m.params.id) : null;
  return (
    <div className="flex min-h-full flex-col md:flex-row">
      <aside className="no-print flex shrink-0 flex-col border-b border-line bg-surface px-3 py-4 md:sticky md:top-0 md:h-screen md:w-[240px] md:border-b-0 md:border-r">
        <Brand />
        <nav aria-label={t("Main")} className="mt-6 space-y-0.5">
          <NavLink to="/prospects" end className={navCls}>
            <FolderOpen className="h-4 w-4" /> {t("Prospects")}
          </NavLink>
          <NavLink to="/catalogue" className={navCls}>
            <BookOpen className="h-4 w-4" /> {t("Data catalogue")}
          </NavLink>
          <NavLink to="/how-it-works" className={navCls}>
            <Workflow className="h-4 w-4" /> {t("How it works")}
          </NavLink>
        </nav>
        {pid !== null && <ProspectNav pid={pid} />}
        <div className="mt-6 space-y-3 md:mt-auto">
          <div className="flex items-start gap-2 rounded-md bg-teal-50 px-2.5 py-2 text-[11.5px] leading-snug text-teal-700">
            <ShieldCheck className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            {t("Processed on this server. No document content is sent to external AI.")}
          </div>
          <LangSwitch />
          <RoleSwitch />
        </div>
      </aside>
      <main className="min-w-0 flex-1">
        <Outlet />
      </main>
    </div>
  );
}

export function ProspectLayout() {
  const pid = Number(useParams().id);
  const { data } = useQuery({ queryKey: ["analysis", pid], queryFn: () => api.analysis(pid) });
  return (
    <div>
      {data?.synthetic && (
        <div className="no-print border-b border-amber-700/20 bg-amber-50 px-4 py-1 text-center text-[12.5px] text-amber-700">
          {t("SYNTHETIC demo data. Banks, client, ISINs and amounts are invented.")}
        </div>
      )}
      <div className="no-print border-b border-line bg-surface">
        <div className="mx-auto flex max-w-[1200px] flex-wrap items-center justify-between gap-3 px-4 py-3.5 sm:px-8">
          <div className="min-w-0">
            <div className="flex items-center gap-1.5 text-[12px] text-subtle">
              <Link to="/prospects" className="hover:text-ink">
                {t("Prospects")}
              </Link>
              <ChevronRight className="h-3 w-3" />
              <span>{data?.prospect.code ?? "…"}</span>
            </div>
            <h1 className="mt-0.5 truncate text-xl font-semibold text-navy-900">
              {data?.prospect.label ?? t("Loading…")}
            </h1>
          </div>
          {data && (
            <div className="flex flex-wrap items-center gap-2 text-[12.5px] text-muted">
              <span className="num font-medium text-ink">{chf(data.aum.total)}</span>
              <span>·</span>
              <span>{t("{n} banks", { n: data.institutions.length })}</span>
              <span>·</span>
              <span>{t("Domicile {code}", { code: data.client_domicile })}</span>
              {data.current.is_complete ? (
                <Badge tone="green">{t("All cost categories evidenced")}</Badge>
              ) : (
                <Badge tone="red">{t("{n} costs not determined", { n: data.current.unknown.length })}</Badge>
              )}
            </div>
          )}
        </div>
      </div>
      <div className="mx-auto max-w-[1200px] px-4 py-6 sm:px-8">
        <Outlet />
      </div>
    </div>
  );
}

export function Page({ children }: { children: ReactNode }) {
  return <div className="mx-auto max-w-[1200px] px-4 py-6 sm:px-8">{children}</div>;
}

export function PageTitle({ title, subtitle, actions }: { title: string; subtitle?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h2 className="text-lg font-semibold text-navy-900">{title}</h2>
        {subtitle && <p className="mt-0.5 max-w-3xl text-[13.5px] text-muted">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}
