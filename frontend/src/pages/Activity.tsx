import { Button, Card, ErrorBox, Spinner, inputCls } from "@/components/ui";
import { type ActivityEvent, activity, auditRole } from "@/lib/api";
import { t } from "@/lib/i18n";
import { useInfiniteQuery } from "@tanstack/react-query";
import { ShieldAlert, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

const ACTION: Record<string, string> = {
  "auth.login": "Signed in",
  "auth.login_failed": "Failed sign-in",
  "auth.logout": "Signed out",
  "auth.password_changed": "Changed their password",
  "auth.mfa_enabled": "Turned on two-step sign-in",
  "auth.mfa_failed": "Wrong authenticator code",
  "document.viewed": "Opened a document",
  "report.downloaded": "Downloaded a client report",
  "report.approved": "Approved a client report",
  "user.created": "Added a person",
  "user.updated": "Changed a person's roles or access",
  "user.password_reset": "Reset a password",
  "user.signed_out": "Signed a person out everywhere",
  "audit.viewed": "Opened the activity log",
  "document.uploaded": "Uploaded a document",
  "document.reclassified": "Changed a document's type",
  "prospect.created": "Started a cost review",
  "prospect.updated": "Edited a cost review",
  "internal.viewed": "Opened internal economics",
  "proposal.saved": "Saved a proposal",
  "request.status": "Updated a document request",
  "fact.accept": "Confirmed a value",
  "fact.correct": "Corrected a value",
  "fact.reset": "Reset a value check",
  "fact.reject": "Rejected a value",
  "crm.contact.created": "Added a contact",
  "crm.contact.updated": "Edited a contact",
  "crm.stage.moved": "Moved a contact to another stage",
  "crm.cost_review.linked": "Linked a cost review to a contact",
};

const KINDS: [string, string][] = [
  ["", "Everything"],
  ["auth.", "Sign-ins"],
  ["document.", "Documents"],
  ["report.", "Client reports"],
  ["fact.", "Value checks"],
  ["user.", "People and access"],
];

/** Activity log (SC-11.8): who signed in, opened, downloaded or changed what, with a tamper check. */
export default function ActivityPage() {
  const [kind, setKind] = useState("");
  const [user, setUser] = useState("");
  const q = useInfiniteQuery({
    queryKey: ["activity", kind, user],
    queryFn: ({ pageParam }) => activity({ action: kind, user: user.trim(), before: pageParam }),
    initialPageParam: undefined as number | undefined,
    getNextPageParam: (last) => (last.events.length >= 100 ? last.events[last.events.length - 1].id : undefined),
  });
  const check = q.data?.pages[0]?.check;
  const events = q.data?.pages.flatMap((p) => p.events) ?? [];

  return (
    <div className="mx-auto max-w-[1100px] px-4 py-6 sm:px-8">
      <h1 className="text-xl font-semibold text-navy-900">{t("Activity log")}</h1>
      <p className="mt-1 mb-5 max-w-2xl text-[13.5px] text-muted">
        {t("Who signed in, opened, downloaded or changed what. Entries cannot be edited or deleted from the app.")}
      </p>
      <div className="space-y-4">
        {check && <CheckBanner check={check} />}
        <div className="flex flex-wrap items-end gap-3">
          <label className="text-[13px] font-medium text-ink">
            {t("Show")}
            <select className={`${inputCls} mt-1 block`} value={kind} onChange={(e) => setKind(e.target.value)}>
              {KINDS.map(([v, l]) => (
                <option key={v} value={v}>
                  {t(l)}
                </option>
              ))}
            </select>
          </label>
          <label className="text-[13px] font-medium text-ink">
            {t("Person (username)")}
            <input
              className={`${inputCls} mt-1 block`}
              value={user}
              onChange={(e) => setUser(e.target.value.toLowerCase())}
              autoCapitalize="none"
            />
          </label>
        </div>
        <Card>
          {q.isLoading ? (
            <Spinner />
          ) : q.error ? (
            <ErrorBox error={q.error} />
          ) : !events.length ? (
            <p className="px-5 py-4 text-[13.5px] text-muted">{t("Nothing recorded yet.")}</p>
          ) : (
            <ul aria-label={t("Activity")}>
              {events.map((e) => (
                <Row key={e.id} e={e} readsData={auditRole() !== "admin"} />
              ))}
            </ul>
          )}
        </Card>
        {q.hasNextPage && (
          <Button variant="outline" loading={q.isFetchingNextPage} onClick={() => q.fetchNextPage()}>
            {t("Show older")}
          </Button>
        )}
      </div>
    </div>
  );
}

function CheckBanner({ check }: { check: { ok: boolean; checked: number; deleted: number; problems: unknown[] } }) {
  if (check.ok)
    return (
      <div className="flex items-center gap-2 text-[13px] text-teal-700">
        <ShieldCheck className="h-4 w-4 shrink-0" />
        {t("Tamper check passed: {n} entries match their seal.", { n: check.checked })}
      </div>
    );
  return (
    <div
      role="alert"
      className="flex gap-2.5 rounded-[var(--radius-card)] border border-red-700/25 bg-red-100/60 px-4 py-3 text-[13px] text-red-700"
    >
      <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />
      <div>
        <div className="font-medium">{t("The log was changed outside the app.")}</div>
        <div>
          {t("{changed} entries changed or added by hand, {deleted} missing. Tell your administrator.", {
            changed: check.problems.length,
            deleted: check.deleted,
          })}
        </div>
      </div>
    </div>
  );
}

function Row({ e, readsData }: { e: ActivityEvent; readsData: boolean }) {
  const label = ACTION[e.action];
  const extra = Object.entries(e.detail ?? {})
    .filter(([, v]) => v !== null && v !== "" && typeof v !== "object")
    .map(([k, v]) => `${k}: ${v}`)
    .join(" · ");
  return (
    <li className="flex flex-wrap items-baseline gap-x-4 gap-y-1 border-b border-line px-4 py-2.5 text-[13px] last:border-0 sm:px-5">
      <time className="num w-40 shrink-0 text-muted" dateTime={e.at}>
        {new Date(e.at).toLocaleString()}
      </time>
      <span className="w-36 shrink-0 font-medium text-ink">{e.user}</span>
      <span className="min-w-0 flex-1">
        {label ? t(label) : <code className="text-[12px]">{e.action}</code>}
        {e.prospect_id && readsData && (
          <Link to={`/p/${e.prospect_id}`} className="ml-2 text-teal-700 underline-offset-2 hover:underline">
            {t("open review")}
          </Link>
        )}
        {extra && <span className="block truncate text-[11.5px] text-subtle">{extra}</span>}
      </span>
    </li>
  );
}
