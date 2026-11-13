import { Page, PageTitle } from "@/components/Shell";
import { Badge, Button, Card, ErrorBox, Field, Spinner, inputCls } from "@/components/ui";
import { ROLE_LABEL, type Role, type UserRow, admin } from "@/lib/api";
import { t } from "@/lib/i18n";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";

const ROLES = Object.keys(ROLE_LABEL) as Role[];

/** Admins create, reset and disable the accounts of their own firm. One-time passwords are shown once. */
export function UsersPage() {
  const qc = useQueryClient();
  const list = useQuery({ queryKey: ["admin-users"], queryFn: admin.users });
  const [username, setUsername] = useState("");
  const [roles, setRoles] = useState<Role[]>(["analyst"]);
  const [isAdmin, setIsAdmin] = useState(false);
  const [secret, setSecret] = useState<{ user: string; pw: string } | null>(null);

  const done = () => qc.invalidateQueries({ queryKey: ["admin-users"] });
  const create = useMutation({
    mutationFn: () => admin.create({ username, roles, admin: isAdmin }),
    onSuccess: (r) => {
      setSecret({ user: r.username, pw: r.one_time_password });
      setUsername("");
      done();
    },
  });
  const act = useMutation({
    mutationFn: ({ u, a }: { u: string; a: "reset" | "disable" | "enable" | "sign-out" }) => admin.action(u, a),
    onSuccess: (r, v) => {
      if (r.one_time_password) setSecret({ user: v.u, pw: r.one_time_password });
      done();
    },
  });

  function submit(e: FormEvent) {
    e.preventDefault();
    create.mutate();
  }

  return (
    <Page>
      <PageTitle
        title={t("Users")}
        subtitle={t(
          "One account per person. New and reset accounts get a one-time password; at first sign-in the person sets their own password and links an authenticator app.",
        )}
      />
      {secret && (
        <Card className="mb-4 p-4">
          <p className="text-[13px] text-ink">
            {t("One-time password for {user}. Give it to the person directly; it is not shown again.", {
              user: secret.user,
            })}
          </p>
          <p className="mt-2 select-all font-mono text-[15px]">{secret.pw}</p>
          <Button className="mt-3" variant="outline" size="sm" onClick={() => setSecret(null)}>
            {t("Done")}
          </Button>
        </Card>
      )}
      <Card className="mb-4 p-4">
        <form onSubmit={submit} className="flex flex-wrap items-end gap-3">
          <Field label={t("Username")}>
            <input className={inputCls} value={username} onChange={(e) => setUsername(e.target.value)} required />
          </Field>
          <fieldset className="flex flex-wrap gap-3 text-[13px]">
            {ROLES.map((r) => (
              <label key={r} className="flex items-center gap-1">
                <input
                  type="checkbox"
                  checked={roles.includes(r)}
                  onChange={(e) => setRoles(e.target.checked ? [...roles, r] : roles.filter((x) => x !== r))}
                />
                {t(ROLE_LABEL[r])}
              </label>
            ))}
            <label className="flex items-center gap-1">
              <input type="checkbox" checked={isAdmin} onChange={(e) => setIsAdmin(e.target.checked)} />
              {t("Admin")}
            </label>
          </fieldset>
          <Button type="submit" loading={create.isPending} disabled={!roles.length}>
            {t("Add user")}
          </Button>
        </form>
        {create.error && <ErrorBox error={create.error} />}
      </Card>
      {list.isLoading && <Spinner label={t("Loading")} />}
      {list.error && <ErrorBox error={list.error} />}
      {act.error && <ErrorBox error={act.error} />}
      <Card>
        <ul className="divide-y divide-line">
          {list.data?.map((u: UserRow) => (
            <li key={u.username} className="flex flex-wrap items-center justify-between gap-2 px-4 py-3">
              <div className="text-[13px]">
                <span className="font-medium text-ink">{u.username}</span>{" "}
                <span className="text-subtle">{u.roles.map((r) => t(ROLE_LABEL[r])).join(", ")}</span>{" "}
                {u.admin && <Badge>{t("Admin")}</Badge>} {!u.active && <Badge tone="red">{t("Disabled")}</Badge>}{" "}
                {u.active && (u.must_change_password || !u.mfa) && <Badge tone="amber">{t("Setup pending")}</Badge>}
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => act.mutate({ u: u.username, a: "reset" })}>
                  {t("Reset")}
                </Button>
                <Button variant="outline" size="sm" onClick={() => act.mutate({ u: u.username, a: "sign-out" })}>
                  {t("Sign out everywhere")}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => act.mutate({ u: u.username, a: u.active ? "disable" : "enable" })}
                >
                  {u.active ? t("Disable") : t("Enable")}
                </Button>
              </div>
            </li>
          ))}
        </ul>
      </Card>
    </Page>
  );
}
