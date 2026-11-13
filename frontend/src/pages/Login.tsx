import { Brand } from "@/components/Shell";
import { Button, Card, Field, Spinner, inputCls } from "@/components/ui";
import { ApiError, type Me, auth, onUnauthorized, setSession, signedOut } from "@/lib/api";
import { t } from "@/lib/i18n";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, type ReactNode, useEffect, useState } from "react";

// Must match pce.security.MFA_REQUIRED: the password was right and the account has an authenticator.
const MFA_REQUIRED = "authenticator code required";

function LoginPage({ onDone }: { onDone: (me: Me) => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [askCode, setAskCode] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      onDone(await auth.login(username, password, code));
      setPassword("");
    } catch (err) {
      const status = err instanceof ApiError ? err.status : 0;
      const msg = err instanceof ApiError ? err.message : "";
      if (msg === MFA_REQUIRED) {
        setAskCode(true); // keep the password: the next submit sends it with the code
      } else {
        setPassword("");
        setCode("");
        setError(
          status === 429
            ? t("Too many failed attempts. Wait 15 minutes and try again.")
            : msg === "wrong authenticator code"
              ? t("Wrong code. Use the newest code in your authenticator app.")
              : status === 401
                ? t("Wrong username or password.")
                : t("Sign-in is not available right now."),
        );
      }
    } finally {
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
          {askCode && (
            <Field label={t("Code from your authenticator app")}>
              <input
                className={inputCls}
                inputMode="numeric"
                autoComplete="one-time-code"
                pattern="[0-9 ]{6,7}"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                required
                // biome-ignore lint/a11y/noAutofocus: the field appears only after the password step
                autoFocus
              />
            </Field>
          )}
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

/** First sign-in: choose a password and link an authenticator app, before anything else. */
function SetupPage({ me, onDone }: { me: Me; onDone: (me: Me) => void }) {
  const key = useQuery({ queryKey: ["setup-key"], queryFn: auth.setupKey, staleTime: Number.POSITIVE_INFINITY });
  const [pw, setPw] = useState("");
  const [pw2, setPw2] = useState("");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (me.must_change_password && pw !== pw2) {
      setError(t("The two passwords differ."));
      return;
    }
    if (!key.data) return;
    setBusy(true);
    setError("");
    try {
      onDone(
        await auth.finishSetup({
          ...(me.must_change_password ? { new_password: pw } : {}),
          secret: key.data.secret,
          proof: key.data.proof,
          code,
        }),
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("Sign-in is not available right now."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-paper px-4">
      <Card className="w-full max-w-[440px] p-6">
        <Brand link={false} />
        <h1 className="mt-6 text-[18px] font-semibold text-ink">{t("Set up your account")}</h1>
        <form onSubmit={submit} className="mt-4 space-y-4">
          {me.must_change_password && (
            <>
              <Field label={t("New password")} hint={t("At least 12 characters. Only you know it.")}>
                <input
                  className={inputCls}
                  type="password"
                  autoComplete="new-password"
                  minLength={12}
                  value={pw}
                  onChange={(e) => setPw(e.target.value)}
                  required
                />
              </Field>
              <Field label={t("Repeat the new password")}>
                <input
                  className={inputCls}
                  type="password"
                  autoComplete="new-password"
                  value={pw2}
                  onChange={(e) => setPw2(e.target.value)}
                  required
                />
              </Field>
            </>
          )}
          <div className="space-y-2 text-[13px] text-ink">
            <p>
              {t(
                "Open an authenticator app (Microsoft Authenticator, Google Authenticator, 1Password) and add an account with this setup key:",
              )}
            </p>
            {key.data ? (
              <p className="select-all break-all rounded bg-paper px-3 py-2 font-mono text-[14px] tracking-wider">
                {key.data.secret.match(/.{1,4}/g)?.join(" ")}
              </p>
            ) : (
              <Spinner label={t("Loading")} />
            )}
            {key.data && (
              <a className="text-[12px] underline" href={key.data.uri}>
                {t("On this phone? Open the authenticator app directly")}
              </a>
            )}
          </div>
          <Field label={t("Code from your authenticator app")}>
            <input
              className={inputCls}
              inputMode="numeric"
              autoComplete="one-time-code"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              required
            />
          </Field>
          {error && (
            <p role="alert" className="text-[13px] text-red-700">
              {error}
            </p>
          )}
          <Button type="submit" className="w-full" loading={busy}>
            {t("Finish setup")}
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
  if (me.data.setup_required) {
    return <SetupPage me={me.data} onDone={(m) => qc.setQueryData(["me"], m)} />;
  }
  return <>{children}</>;
}
