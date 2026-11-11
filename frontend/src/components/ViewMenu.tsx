import { t } from "@/lib/i18n";
import { SlidersHorizontal } from "lucide-react";
import { useState } from "react";

/** Sections an analyst has hidden on a page, remembered in this browser only. */
export function useHidden(page: string): [string[], (h: string[]) => void] {
  const key = `feelens.view.${page}`;
  const [hidden, setHidden] = useState<string[]>(() => {
    try {
      return JSON.parse(localStorage.getItem(key) ?? "[]");
    } catch {
      return [];
    }
  });
  const save = (h: string[]) => {
    setHidden(h);
    try {
      localStorage.setItem(key, JSON.stringify(h));
    } catch {
      // storage unavailable: the choice lasts for this page view
    }
  };
  return [hidden, save];
}

export function ViewMenu({
  sections,
  hidden,
  onChange,
}: { sections: { key: string; label: string }[]; hidden: string[]; onChange: (h: string[]) => void }) {
  return (
    <details className="relative">
      <summary className="flex cursor-pointer list-none items-center gap-1.5 rounded-md border border-line bg-surface px-3 py-1.5 text-[13px] text-muted hover:text-ink">
        <SlidersHorizontal className="h-3.5 w-3.5" /> {t("Customise view")}
      </summary>
      <div className="absolute right-0 z-30 mt-1 w-64 rounded-lg border border-line bg-surface p-2 shadow-lg">
        <div className="px-2 pb-1 text-[12px] text-subtle">{t("Sections shown on this page")}</div>
        {sections.map((s) => (
          <label key={s.key} className="flex items-center gap-2 rounded px-2 py-1 text-[13px] hover:bg-paper">
            <input
              type="checkbox"
              className="accent-teal-700"
              checked={!hidden.includes(s.key)}
              onChange={(e) => onChange(e.target.checked ? hidden.filter((k) => k !== s.key) : [...hidden, s.key])}
            />
            {t(s.label)}
          </label>
        ))}
      </div>
    </details>
  );
}
