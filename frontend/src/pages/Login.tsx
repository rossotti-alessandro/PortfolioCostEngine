import { Brand } from "@/components/Shell";
import { Button, Card, Field, Spinner, inputCls } from "@/components/ui";
import { ApiError, type Me, auth, onUnauthorized, setSession, signedOut } from "@/lib/api";
import { t } from "@/lib/i18n";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, type ReactNode, useEffect, useState } from "react";

function LoginPage({ onDone }: { onDone: (me: Me) => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      onDone(await auth.login(username, password));
    } catch (err) {
      const status = err instanceof ApiError ? err.status : 0;
      setError(
        status === 429
          ? t("Too many failed attempts. Wait 15 minutes and try again.")
          : status === 401
            ? t("Wrong username or password.")
            : t("Sign-in is not available right now."),
      );
    } finally {
      setPassword("");
      setBusy(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-paper px-4">
      <Card className="w-full max-w-[380px] p-6">
        <Brand link={false} />
        <h1 className="mt-6 text-[18px] font-semibold text-ink">{t("Sign in")}</h1>
        <form onSubmit={submit} className="mt-4 space-y-3">
          <Field label={t("Username")}>
            <input
              className={inputCls}
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </Field>
          <Field label={t("Password")}>
            <input
              className={inputCls}
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </Field>
          {error && (
            <p role="alert" className="text-[13px] text-red-700">
              {error}
            </p>
          )}
          <Button type="submit" className="w-full" loading={busy}>
            {t("Sign in")}
          </Button>
        </form>
      </Card>
    </main>
  );
}

/** First sign-in with a one-time password: the person chooses their own before anything else. */
function ChangePasswordPage({ me, onDone }: { me: Me; onDone: (me: Me) => void }) {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [again, setAgain] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    if (next.length < 12) return setError(t("Use at least 12 characters."));
    if (next !== again) return setError(t("The two new passwords differ."));
    setBusy(true);
    try {
      onDone(await auth.changePassword(current, next));
    } catch (err) {
      const status = err instanceof ApiError ? err.status : 0;
      setError(status === 403 ? t("The one-time password is wrong.") : t("The password could not be changed."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-paper px-4">
      <Card className="w-full max-w-[380px] p-6">
        <Brand link={false} />
        <h1 className="mt-6 text-[18px] font-semibold text-ink">{t("Choose your password")}</h1>
        <p className="mt-1 text-[13px] text-muted">
          {t("Welcome, {name}. Replace the one-time password you were given with your own.", {
            name: me.display_name || me.username,
          })}
        </p>
        <form onSubmit={submit} className="mt-4 space-y-3">
          <Field label={t("One-time password")}>
            <input
              className={inputCls}
              type="password"
              autoComplete="current-password"
              value={current}
              onChange={(e) => setCurrent(e.target.value)}
              required
            />
          </Field>
          <Field label={t("New password (12+ characters)")}>
            <input
              className={inputCls}
              type="password"
              autoComplete="new-password"
              minLength={12}
              value={next}
              onChange={(e) => setNext(e.target.value)}
              required
            />
          </Field>
          <Field label={t("New password again")}>
            <input
              className={inputCls}
              type="password"
              autoComplete="new-password"
              value={again}
              onChange={(e) => setAgain(e.target.value)}
              required
            />
          </Field>
          {error && (
            <p role="alert" className="text-[13px] text-red-700">
              {error}
            </p>
          )}
          <Button type="submit" className="w-full" loading={busy}>
            {t("Save password")}
          </Button>
        </form>
      </Card>
    </main>
  );
}

/** Shows the sign-in page until the server confirms a session, then the app. */
export function RequireAuth({ children }: { children: ReactNode }) {
  const qc = useQueryClient();
  const me = useQuery({ queryKey: ["me"], queryFn: auth.me, retry: false, staleTime: Number.POSITIVE_INFINITY });
  useEffect(() => onUnauthorized(() => signedOut(qc)), [qc]);
  if (me.isLoading) return <Spinner label={t("Loading")} />;
  if (!me.data) {
    return (
      <LoginPage
        onDone={(m) => {
          setSession(m);
          qc.setQueryData(["me"], m);
        }}
      />
    );
  }
  setSession(me.data);
  if (me.data.must_change_password)
    return (
      <ChangePasswordPage
        me={me.data}
        onDone={(m) => {
          setSession(m);
          qc.setQueryData(["me"], m);
        }}
      />
    );
  return <>{children}</>;
}
