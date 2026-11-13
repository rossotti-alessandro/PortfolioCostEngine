import { type Me, ROLE_LABEL, type Role, allowedRoleList, api, auth, getRole, setRole, signedOut } from "@/lib/api";
import { PRODUCT } from "@/lib/brand";
import { chf, cn } from "@/lib/format";
import { setLang, t, useLang } from "@/lib/i18n";
import { crm } from "@/pages/crm/api";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  BookOpen,
  Check,
  ChevronRight,
  ChevronsUpDown,
  FolderOpen,
  Lock,
  LogOut,
  Percent,
  ShieldCheck,
  Users,
} from "lucide-react";
import { type ReactNode, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useParams } from "react-router-dom";
import { Badge, InfoTip } from "./ui";

/** Logo and name; a link home inside the app, plain on the sign-in page (no router there). */
export function Brand({ link = true }: { link?: boolean }) {
  const inner = (
    <>
      <img src="/favicon.svg" alt="" className="h-7 w-7" />
      <div className="leading-tight">
        <div className="text-[15px] font-semibold tracking-tight text-navy-900">{PRODUCT.name}</div>
        <div className="text-[11px] text-subtle">{t(PRODUCT.tagline)}</div>
      </div>
    </>
  );
  const cls = "flex items-center gap-2.5 px-2";
  return link ? (
    <Link to="/crm" className={cls}>
      {inner}
    </Link>
  ) : (
    <div className={cls}>{inner}</div>
  );
}

function LangSwitch() {
  const lang = useLang();
  return (
    <fieldset
      className="flex rounded-[var(--radius-control)] border border-line bg-surface p-0.5 text-[12px]"
      aria-label={t("Language")}
    >
      {(["en", "it"] as const).map((l) => (
        <button
          key={l}
          type="button"
          aria-pressed={lang === l}
          onClick={() => setLang(l)}
          className={cn(
            "flex-1 rounded-[3px] px-2 py-1 font-medium",
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
  const roles = allowedRoleList();
  if (roles.length < 2) return null; // nothing to switch: the account holds one role
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
        className="mt-1 h-8 w-full rounded-[var(--radius-control)] border border-line-strong bg-surface px-2 text-[13px] text-ink focus:outline-none focus:ring-2 focus:ring-teal-600/20"
      >
        {roles.map((r) => (
          <option key={r} value={r}>
            {t(ROLE_LABEL[r])}
          </option>
        ))}
      </select>
    </label>
  );
}

/** Language, demo role and sign-out in one menu, so the sidebar keeps only places to go. */
function AccountMenu() {
  const qc = useQueryClient();
  const lang = useLang();
  const me = qc.getQueryData<Me>(["me"]);
  return (
    <details className="group relative">
      <summary
        aria-label={t("Account menu")}
        className="flex cursor-pointer list-none items-center gap-2 rounded-[var(--radius-control)] px-2 py-1.5 hover:bg-paper"
      >
        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-navy-900 text-[12px] font-semibold uppercase text-white">
          {(me?.username ?? "?").slice(0, 1)}
        </span>
        <span className="min-w-0 flex-1 leading-tight">
          <span className="block truncate text-[13px] font-medium text-ink">{me?.username ?? "…"}</span>
          <span className="block truncate text-[11.5px] text-subtle">
            {lang.toUpperCase()} · {t(ROLE_LABEL[getRole()])}
          </span>
        </span>
        <ChevronsUpDown className="h-3.5 w-3.5 shrink-0 text-subtle" aria-hidden />
      </summary>
      <div className="absolute bottom-full left-0 z-30 mb-1 w-full space-y-3 rounded-[var(--radius-card)] border border-line bg-surface p-3 shadow-lg">
        <LangSwitch />
        <RoleSwitch />
        <button
          type="button"
          onClick={async () => {
            await auth.logout().catch(() => undefined);
            signedOut(qc);
          }}
          className="flex w-full items-center gap-1.5 rounded-[var(--radius-control)] px-1.5 py-1 text-[12.5px] font-medium text-muted hover:bg-paper hover:text-ink"
        >
          <LogOut className="h-3.5 w-3.5" /> {t("Sign out")}
        </button>
      </div>
    </details>
  );
}

const STEPS = [
  { to: "documents", label: "Documents" },
  { to: "review", label: "Check values" },
  { to: "costs", label: "Costs" },
  { to: "compare", label: "Compare" },
  { to: "report", label: "Report" },
];

const navCls = ({ isActive }: { isActive: boolean }) =>
  cn(
    "flex items-center gap-2.5 rounded-[var(--radius-control)] px-2.5 py-1.5 text-[13.5px] font-medium",
    isActive ? "bg-navy-100 text-navy-900" : "text-muted hover:bg-paper hover:text-ink",
  );

/** The five steps of a review across the top of the workspace: done ticks and what is left to check. */
function StepBar({ pid }: { pid: number }) {
  const { data } = useQuery({ queryKey: ["analysis", pid], queryFn: () => api.analysis(pid) });
  const { data: docs } = useQuery({ queryKey: ["documents", pid], queryFn: () => api.documents(pid) });
  const toCheck = data ? data.review.facts - data.review.reviewed - data.review.rejected : 0;
  const done: Record<string, boolean> = {
    documents: (docs?.length ?? 0) > 0,
    review: !!data && data.review.facts > 0 && toCheck <= 0,
    costs: !!data && data.current.is_complete,
    compare: false,
    report: !!data?.approval?.valid,
  };
  return (
    <nav aria-label={t("Review workflow")} className="-mb-px flex items-end gap-1 overflow-x-auto">
      {STEPS.map((s, i) => (
        <NavLink
          key={s.to}
          to={`/p/${pid}/${s.to}`}
          className={({ isActive }) =>
            cn(
              "flex shrink-0 items-center gap-2 border-b-2 px-3 pb-2.5 pt-1 text-[13.5px] font-medium",
              isActive ? "border-navy-900 text-navy-900" : "border-transparent text-muted hover:text-ink",
            )
          }
        >
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
                {done[s.to] ? <Check className="h-3 w-3" aria-label={t("done")} /> : i + 1}
              </span>
              {t(s.label)}
              {s.to === "review" && toCheck > 0 && (
                <span
                  title={t("{n} values not yet checked by a person", { n: toCheck })}
                  className="num rounded-[3px] bg-amber-50 px-1.5 text-[11.5px] font-semibold text-amber-700 ring-1 ring-inset ring-amber-700/20"
                >
                  {toCheck}
                </span>
              )}
            </>
          )}
        </NavLink>
      ))}
      <NavLink
        to={`/p/${pid}/internal`}
        className={({ isActive }) =>
          cn(
            "ml-auto flex shrink-0 items-center gap-1.5 border-b-2 px-3 pb-2.5 pt-1 text-[12.5px] font-medium",
            isActive ? "border-navy-900 text-navy-900" : "border-transparent text-subtle hover:text-ink",
          )
        }
      >
        <Lock className="h-3.5 w-3.5" /> {t("Internal economics")}
      </NavLink>
    </nav>
  );
}

/** Left navigation (240px) per DESIGN_SYSTEM.md §3; collapses to a top block on small screens. */
export function AppShell() {
  const path = useLocation().pathname;
  return (
    <div className="flex min-h-full flex-col md:flex-row">
      <aside className="no-print flex shrink-0 flex-col border-b border-line bg-surface px-3 py-4 md:sticky md:top-0 md:h-screen md:w-[240px] md:border-b-0 md:border-r">
        <Brand />
        <nav aria-label={t("Main")} className="mt-6 space-y-0.5">
          <NavLink to="/crm" className={navCls}>
            <Users className="h-4 w-4" /> {t("Clients & pipeline")}
          </NavLink>
          <NavLink to="/prospects" end className={navCls}>
            <FolderOpen className="h-4 w-4" /> {t("Cost reviews")}
          </NavLink>
          <NavLink
            to="/catalogue"
            className={() => navCls({ isActive: path.startsWith("/catalogue") || path.startsWith("/how-it-works") })}
          >
            <BookOpen className="h-4 w-4" /> {t("Library")}
          </NavLink>
          <NavLink to="/tariff" className={navCls}>
            <Percent className="h-4 w-4" /> {t("Firm tariff")}
          </NavLink>
        </nav>
        <div className="mt-6 space-y-2 md:mt-auto">
          <div className="flex items-center gap-1.5 px-2.5 text-[11.5px] text-teal-700">
            <ShieldCheck className="h-3.5 w-3.5 shrink-0" />
            {t("Local only")}
            <InfoTip>{t("Processed on this server. No document content is sent to external AI.")}</InfoTip>
          </div>
          <AccountMenu />
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
  const contact = useQuery({ queryKey: ["crm-by-prospect", pid], queryFn: () => crm.byProspect(pid), retry: false });
  return (
    <div>
      {data?.synthetic && (
        <div className="no-print border-b border-amber-700/20 bg-amber-50 px-4 py-1 text-center text-[12.5px] text-amber-700">
          {t("SYNTHETIC demo data. Banks, client, ISINs and amounts are invented.")}
        </div>
      )}
      <div className="no-print border-b border-line bg-surface">
        <div className="mx-auto flex max-w-[1200px] flex-wrap items-center justify-between gap-3 px-4 pb-2 pt-3.5 sm:px-8">
          <div className="min-w-0">
            <div className="flex items-center gap-1.5 text-[12px] text-subtle">
              {contact.data ? (
                <>
                  <Link to="/crm" className="hover:text-ink">
                    {t("Clients & pipeline")}
                  </Link>
                  <ChevronRight className="h-3 w-3" />
                  <Link to={`/crm/c/${contact.data.contact_id}`} className="hover:text-ink">
                    {contact.data.name}
                  </Link>
                </>
              ) : (
                <Link to="/prospects" className="hover:text-ink">
                  {t("Cost reviews")}
                </Link>
              )}
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
              {data.holdings.length === 0 ? (
                <Badge tone="amber">
                  {t(
                    data.documents.some((d) => d.doc_type === "portfolio_statement")
                      ? "No position valued in CHF yet"
                      : "No statement of assets yet",
                  )}
                </Badge>
              ) : data.current.is_complete ? (
                <Badge tone="green">{t("All cost categories evidenced")}</Badge>
              ) : (
                <Badge tone="red">{t("{n} costs not determined", { n: data.current.unknown.length })}</Badge>
              )}
            </div>
          )}
        </div>
        <div className="mx-auto max-w-[1200px] px-2 sm:px-6">
          <StepBar pid={pid} />
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
      <div className="flex items-center gap-1.5">
        <h2 className="text-lg font-semibold text-navy-900">{title}</h2>
        {subtitle && <InfoTip>{subtitle}</InfoTip>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}
