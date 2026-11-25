import { Badge, Button, Card, Dialog, ErrorBox, Field, Spinner, inputCls } from "@/components/ui";
import { type Me, ROLE_HELP, ROLE_LABEL, type Role, type TeamMember, admin } from "@/lib/api";
import { cn } from "@/lib/format";
import { t } from "@/lib/i18n";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Copy, KeyRound, LogOut, Pencil, Plus, UserCheck, UserX } from "lucide-react";
import { useState } from "react";

const ALL: Role[] = ["analyst", "senior", "relationship_manager", "viewer", "admin"];

/** Team & access (SC-11.12): who can sign in, with which rights. Admins only; the server checks it too. */
export default function AdminPage() {
  const qc = useQueryClient();
  const me = qc.getQueryData<Me>(["me"]);
  const users = useQuery({ queryKey: ["admin", "users"], queryFn: admin.users });
  const [adding, setAdding] = useState(false);
  const [editing, setEditing] = useState<TeamMember | null>(null);
  const [secret, setSecret] = useState<{ username: string; password: string } | null>(null);
  const done = () => qc.invalidateQueries({ queryKey: ["admin"] });
  const act = useMutation({
    mutationFn: async ({ u, what }: { u: TeamMember; what: "reset" | "signout" | "toggle" }) => {
      if (what === "reset") {
        const r = await admin.resetPassword(u.username);
        setSecret({ username: u.username, password: r.one_time_password });
      } else if (what === "signout") await admin.signOut(u.username);
      else await admin.update(u.username, { active: !u.active });
    },
    onSuccess: done,
  });

  return (
    <div className="mx-auto max-w-[1100px] px-4 py-6 sm:px-8">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-navy-900">{t("Team & access")}</h1>
          <p className="mt-1 max-w-2xl text-[13.5px] text-muted">
            {t("Who can sign in and what they may do. A new role or a deactivation ends the person's open sessions.")}
          </p>
        </div>
        <Button onClick={() => setAdding(true)}>
          <Plus className="h-4 w-4" /> {t("Add a person")}
        </Button>
      </div>
      <div className="space-y-4">
        {act.error && <ErrorBox error={act.error} />}
        <Card>
          {users.isLoading ? (
            <Spinner />
          ) : users.error ? (
            <ErrorBox error={users.error} />
          ) : !users.data?.users.length ? (
            <p className="px-5 py-4 text-[13.5px] text-muted">
              {t("Only the server's break-glass admin can sign in. Add your colleagues here.")}
            </p>
          ) : (
            <ul aria-label={t("People")}>
              {users.data.users.map((u) => (
                <li
                  key={u.username}
                  className="flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-line px-4 py-3 last:border-0 sm:px-5"
                >
                  <div className="min-w-[12rem] flex-1">
                    <div
                      className={cn("text-[14px] font-medium", u.active ? "text-navy-900" : "text-subtle line-through")}
                    >
                      {u.display_name || u.username}
                    </div>
                    <div className="text-[12px] text-muted">
                      {u.username}
                      {!u.active && ` · ${t("deactivated")}`}
                      {u.active && u.must_change_password && ` · ${t("has not chosen a password yet")}`}
                      {u.live_sessions > 0 && ` · ${t("{n} signed in", { n: u.live_sessions })}`}
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {u.roles.map((r) => (
                      <Badge key={r} tone={r === "admin" ? "amber" : r === "viewer" ? "grey" : "teal"}>
                        {t(ROLE_LABEL[r])}
                      </Badge>
                    ))}
                  </div>
                  <div className="flex gap-1">
                    <Button
                      size="icon"
                      variant="ghost"
                      aria-label={t("Edit {name}", { name: u.username })}
                      onClick={() => setEditing(u)}
                    >
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button
                      size="icon"
                      variant="ghost"
                      aria-label={t("New one-time password for {name}", { name: u.username })}
                      onClick={() => act.mutate({ u, what: "reset" })}
                    >
                      <KeyRound className="h-4 w-4" />
                    </Button>
                    <Button
                      size="icon"
                      variant="ghost"
                      aria-label={t("Sign {name} out everywhere", { name: u.username })}
                      disabled={!u.live_sessions}
                      onClick={() => act.mutate({ u, what: "signout" })}
                    >
                      <LogOut className="h-4 w-4" />
                    </Button>
                    {u.username !== me?.username && (
                      <Button
                        size="icon"
                        variant="ghost"
                        aria-label={t(u.active ? "Deactivate {name}" : "Reactivate {name}", { name: u.username })}
                        onClick={() => act.mutate({ u, what: "toggle" })}
                      >
                        {u.active ? <UserX className="h-4 w-4" /> : <UserCheck className="h-4 w-4" />}
                      </Button>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <details className="rounded-[var(--radius-card)] border border-line bg-surface px-5 py-3 text-[13px]">
          <summary className="cursor-pointer font-medium text-navy-900">{t("What each role may do")}</summary>
          <dl className="mt-2 space-y-1.5">
            {ALL.map((r) => (
              <div key={r}>
                <dt className="inline font-medium text-ink">{t(ROLE_LABEL[r])}: </dt>
                <dd className="inline text-muted">{t(ROLE_HELP[r])}</dd>
              </div>
            ))}
            <p className="pt-1 text-muted">
              {t("A client report is approved by a senior who did not upload documents or correct values in it.")}
            </p>
          </dl>
        </details>
      </div>
      {adding && (
        <PersonDialog
          onClose={() => setAdding(false)}
          onSaved={(r) => {
            if (r) setSecret(r);
            done();
          }}
        />
      )}
      {editing && (
        <PersonDialog
          person={editing}
          self={editing.username === me?.username}
          onClose={() => setEditing(null)}
          onSaved={done}
        />
      )}
      {secret && <SecretDialog {...secret} onClose={() => setSecret(null)} />}
    </div>
  );
}

function PersonDialog({
  person,
  self,
  onClose,
  onSaved,
}: {
  person?: TeamMember;
  self?: boolean;
  onClose: () => void;
  onSaved: (r?: { username: string; password: string }) => void;
}) {
  const [username, setUsername] = useState(person?.username ?? "");
  const [name, setName] = useState(person?.display_name ?? "");
  const [roles, setRoles] = useState<Role[]>(person?.roles ?? ["analyst"]);
  const m = useMutation({
    mutationFn: async () => {
      if (person) {
        await admin.update(person.username, { roles, display_name: name });
        return undefined;
      }
      const r = await admin.create({ username, display_name: name, roles });
      return { username: r.username, password: r.one_time_password };
    },
    onSuccess: (r) => {
      onSaved(r);
      onClose();
    },
  });
  return (
    <Dialog
      open
      onOpenChange={(o) => !o && onClose()}
      title={person ? t("Edit {name}", { name: person.username }) : t("Add a person")}
      description={
        person
          ? t("A role change ends the person's open sessions.")
          : t("They get a one-time password and choose their own at first sign-in.")
      }
    >
      <form
        className="space-y-3"
        onSubmit={(e) => {
          e.preventDefault();
          m.mutate();
        }}
      >
        {!person && (
          <Field label={t("Username")}>
            <input
              className={inputCls}
              value={username}
              onChange={(e) => setUsername(e.target.value.toLowerCase())}
              placeholder="m.rossi"
              autoCapitalize="none"
              required
            />
          </Field>
        )}
        <Field label={t("Full name")}>
          <input className={inputCls} value={name} onChange={(e) => setName(e.target.value)} />
        </Field>
        <fieldset>
          <legend className="mb-1 text-[13px] font-medium text-ink">{t("Roles")}</legend>
          <div className="space-y-1.5">
            {ALL.map((r) => (
              <label key={r} className="flex items-start gap-2 text-[13px]">
                <input
                  type="checkbox"
                  className="mt-0.5"
                  checked={roles.includes(r)}
                  disabled={self && r === "admin"}
                  onChange={(e) => setRoles(e.target.checked ? [...roles, r] : roles.filter((x) => x !== r))}
                />
                <span>
                  <span className="font-medium text-ink">{t(ROLE_LABEL[r])}</span>
                  <span className="block text-[12px] text-muted">{t(ROLE_HELP[r])}</span>
                </span>
              </label>
            ))}
          </div>
        </fieldset>
        {m.error && <ErrorBox error={m.error} />}
        <div className="flex justify-end gap-2 pt-1">
          <Button variant="outline" onClick={onClose}>
            {t("Cancel")}
          </Button>
          <Button type="submit" loading={m.isPending} disabled={!roles.length}>
            {person ? t("Save") : t("Add and show password")}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}

/** The one-time password, shown once. It is never stored in the page or sent anywhere else. */
function SecretDialog({ username, password, onClose }: { username: string; password: string; onClose: () => void }) {
  const [copied, setCopied] = useState(false);
  return (
    <Dialog
      open
      onOpenChange={(o) => !o && onClose()}
      title={t("One-time password for {name}", { name: username })}
      description={t("Give it to the person in private (not by email). It is shown only now.")}
    >
      <div className="flex items-center gap-2">
        <code
          className="num flex-1 rounded-[var(--radius-control)] border border-line bg-paper px-3 py-2 text-[15px]"
          data-testid="one-time-password"
        >
          {password}
        </code>
        <Button
          variant="outline"
          onClick={async () => {
            await navigator.clipboard?.writeText(password).catch(() => undefined);
            setCopied(true);
          }}
        >
          <Copy className="h-4 w-4" /> {copied ? t("Copied") : t("Copy")}
        </Button>
      </div>
      <div className="mt-4 flex justify-end">
        <Button onClick={onClose}>{t("Done")}</Button>
      </div>
    </Dialog>
  );
}
