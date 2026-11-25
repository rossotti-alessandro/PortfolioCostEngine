import { Brand } from "@/components/Shell";
import { Button, Card, Field, Spinner, inputCls } from "@/components/ui";
import { ApiError, MFA_REQUIRED, type Me, auth, onUnauthorized, setSession, signedOut } from "@/lib/api";
import { t } from "@/lib/i18n";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, type ReactNode, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

function LoginPage({ onDone }: { onDone: (me: Me) => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [needCode, setNeedCode] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      onDone(await auth.login(username, password, needCode ? code : undefined));
    } catch (err) {
      const status = err instanceof ApiError ? err.status : 0;
      if (status === 401 && err instanceof ApiError && err.message === MFA_REQUIRED) {
        setNeedCode(true); // the password was right: keep it and ask for the code
        return;
      }
      setError(
        status === 429
          ? t("Too many failed attempts. Wait 15 minutes and try again.")
          : status === 401
            ? needCode
              ? t("Wrong username, password or code.")
              : t("Wrong username or password.")
            : t("Sign-in is not available right now."),
      );
      setPassword("");
      setCode("");
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
          {needCode && (
            <Field label={t("Code from your authenticator app")}>
              <input
                className={inputCls}
                inputMode="numeric"
                autoComplete="one-time-code"
                pattern="[0-9 ]{6,7}"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                required
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

/** Add the authenticator app: a key to scan or tap on the phone, then one code to prove it works. */
export function MfaSetup({ onDone, required }: { onDone: (me: Me) => void; required?: boolean }) {
  const key = useQuery({ queryKey: ["mfa-key"], queryFn: auth.mfaStart, staleTime: Number.POSITIVE_INFINITY });
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!key.data) return;
    setBusy(true);
    setError("");
    try {
      onDone(await auth.mfaFinish({ secret: key.data.secret, proof: key.data.proof, code }));
    } catch {
      setError(t("The code does not match. Check that the phone's clock is right and try the next code."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="w-full max-w-[420px] p-6">
      <h1 className="text-[18px] font-semibold text-ink">{t("Two-step sign-in")}</h1>
      <p className="mt-1 text-[13px] text-muted">
        {required
          ? t("Your firm asks for a code from your phone at every sign-in. Set it up once.")
          : t("Ask for a code from your phone at every sign-in, so a stolen password is not enough.")}
      </p>
      {key.isLoading ? (
        <Spinner />
      ) : !key.data ? (
        <p className="mt-3 text-[13px] text-red-700">{t("Setup is not available right now.")}</p>
      ) : (
        <form onSubmit={submit} className="mt-4 space-y-3 text-[13px]">
          <ol className="list-decimal space-y-2 pl-5 text-ink">
            <li>{t("Install an authenticator app (Microsoft Authenticator, Google Authenticator or similar).")}</li>
            <li>
              {t("On this phone:")}{" "}
              <a className="font-medium text-teal-700 underline" href={key.data.uri}>
                {t("add FeeLens to the app")}
              </a>
              . {t("On a computer, add this key in the app:")}
              <code className="num mt-1 block rounded-[var(--radius-control)] border border-line bg-paper px-2 py-1.5 text-[13px] tracking-wider">
                {key.data.secret.match(/.{1,4}/g)?.join(" ")}
              </code>
            </li>
            <li>{t("Type the 6-digit code the app shows.")}</li>
          </ol>
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
            <p role="alert" className="text-red-700">
              {error}
            </p>
          )}
          <Button type="submit" className="w-full" loading={busy}>
            {t("Turn on two-step sign-in")}
          </Button>
        </form>
      )}
    </Card>
  );
}

/** Optional opt-in from the account menu (when the firm does not require it). */
export function TwoStepPage() {
  const qc = useQueryClient();
  const nav = useNavigate();
  return (
    <div className="flex justify-center px-4 py-8">
      <MfaSetup
        onDone={(m) => {
          setSession(m);
          qc.setQueryData(["me"], m);
          nav("/");
        }}
      />
    </div>
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
  if (me.data.mfa_setup_needed)
    return (
      <main className="flex min-h-screen items-center justify-center bg-paper px-4">
        <MfaSetup
          required
          onDone={(m) => {
            setSession(m);
            qc.setQueryData(["me"], m);
          }}
        />
      </main>
    );
  return <>{children}</>;
}
