/** Which file is on the stage. One document is a slim strip; several become a dropdown so the list never takes a column. */

import { DOC_TYPES } from "@/lib/format";
import { t } from "@/lib/i18n";
import type { DocumentRow } from "@/lib/types";

export function DocumentSwitcher({
  docs,
  docId,
  onSelect,
}: {
  docs: DocumentRow[];
  docId: number | undefined;
  onSelect: (id: number) => void;
}) {
  const doc = docs.find((d) => d.id === docId) ?? docs[0];
  if (!doc) return null;
  const caption = [doc.profile.institution, doc.filename].filter(Boolean).join(" · ");

  if (docs.length === 1) {
    return (
      <div className="min-w-0">
        <div className="truncate text-[13.5px] font-semibold text-navy-900">
          {t(DOC_TYPES[doc.doc_type] ?? doc.doc_type)}
        </div>
        <div className="truncate text-[11.5px] text-subtle" title={doc.sha256}>
          {caption}
        </div>
      </div>
    );
  }

  return (
    <div className="min-w-0 flex-1">
      <select
        aria-label={t("Document")}
        value={doc.id}
        onChange={(e) => onSelect(Number(e.target.value))}
        className="h-8 w-full max-w-xl truncate rounded-[var(--radius-control)] border border-line-strong bg-surface px-2 text-[13px] font-medium text-ink focus:outline-none focus:ring-2 focus:ring-teal-600/20"
      >
        {docs.map((d) => (
          <option key={d.id} value={d.id}>
            {t(DOC_TYPES[d.doc_type] ?? d.doc_type)} — {d.filename}
          </option>
        ))}
      </select>
      <div className="mt-0.5 truncate text-[11.5px] text-subtle">
        {caption} · {t("{n} documents", { n: docs.length })}
      </div>
    </div>
  );
}
