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
  return <>{children}</>;
}
