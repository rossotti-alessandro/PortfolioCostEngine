import { useSyncExternalStore } from "react";
import { IT } from "./it";

/** UI language. English source strings are the keys; Italian comes from ./it. Missing keys fall back to English. */
export type Lang = "en" | "it";

function initial(): Lang {
  try {
    return localStorage.getItem("feelens.lang") === "it" ? "it" : "en";
  } catch {
    return "en";
  }
}

let lang: Lang = initial();
const subs = new Set<() => void>();

export function getLang(): Lang {
  return lang;
}

export function setLang(l: Lang) {
  lang = l;
  try {
    localStorage.setItem("feelens.lang", l);
  } catch {
    // private mode: the choice lasts for this page only
  }
  if (typeof document !== "undefined") document.documentElement.lang = l;
  for (const f of subs) f();
}

export function useLang(): Lang {
  return useSyncExternalStore(
    (cb) => {
      subs.add(cb);
      return () => subs.delete(cb);
    },
    () => lang,
  );
}

/** t("Saved {n} files", { n: 3 }) */
export function t(en: string, vars?: Record<string, string | number>): string {
  const s = lang === "it" ? (IT[en] ?? en) : en;
  return vars ? s.replace(/\{(\w+)\}/g, (_m, k: string) => String(vars[k] ?? `{${k}}`)) : s;
}
