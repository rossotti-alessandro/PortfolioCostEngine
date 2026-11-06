import { api } from "@/lib/api";
import { LAYER, MEASUREMENT, chf } from "@/lib/format";
import { t } from "@/lib/i18n";
import type { Analysis, Atom } from "@/lib/types";
import { useQuery } from "@tanstack/react-query";
import { ExternalLink } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { PdfEvidence, SheetEvidence } from "./EvidenceViewer";
import { Badge, Button, Dialog, Spinner, StatusBadge } from "./ui";

/** Click-through from any cost number to its formula and the highlighted source region. */
export function AtomEvidenceDialog({
  atom,
  analysis,
  onClose,
}: { atom: Atom | null; analysis: Analysis; onClose: () => void }) {
  const pid = Number(useParams().id);
  const factIds = atom?.evidence_fact_ids ?? [];
  const [idx, setIdx] = useState(0);
  const factId = factIds[Math.min(idx, factIds.length - 1)];
  const docId = useQuery({
    queryKey: ["fact-doc", factId],
    enabled: !!factId,
    queryFn: async () => {
      for (const d of analysis.documents) {
        const fs = await api.facts(d.id);
        const f = fs.find((x) => x.id === factId);
        if (f) return { doc: d, facts: fs, fact: f };
      }
      return null;
    },
  });
  const children = atom
    ? analysis.current.atoms.filter((a) => a.included_in === atom.id || a.corroborates === atom.id)
    : [];
  return (
    <Dialog
      open={!!atom}
      onOpenChange={(o) => !o && onClose()}
      title={atom?.label ?? ""}
      description={atom ? `${atom.fee_label} · ${LAYER[atom.layer] ? t(LAYER[atom.layer].name) : atom.layer}` : ""}
      wide
    >
      {atom && (
        <div className="grid gap-4 md:grid-cols-[320px_1fr]">
          <div className="space-y-3 text-[13px]">
            <div>
              <div className="text-[12px] text-subtle">{t("Annual amount")}</div>
              <div className="num text-2xl font-semibold text-navy-900">
                {atom.amount === null ? t("Not determined") : chf(atom.amount, 2)}
              </div>
              {atom.bps && <div className="num text-muted">{t("{bps} bps of assets reviewed", { bps: atom.bps })}</div>}
            </div>
            <div className="flex flex-wrap gap-1.5">
              <StatusBadge m={atom.measurement} />
              <Badge>
                {atom.incidence === "embedded"
                  ? t("Inside product price (NAV)")
                  : atom.incidence === "tax"
                    ? t("Tax")
                    : t("Debited from account")}
              </Badge>
              {atom.role === "included_in_parent" && <Badge tone="violet">{t("Included in parent · not added")}</Badge>}
              {atom.role === "corroborating" && <Badge tone="violet">{t("Second evidence · counted once")}</Badge>}
              {atom.role === "not_a_paid_cost" && <Badge>{t("Not a paid cost · not counted")}</Badge>}
            </div>
            <p className="text-[12.5px] text-muted">
              {MEASUREMENT[atom.measurement] && t(MEASUREMENT[atom.measurement].help)}
            </p>
            {atom.formula && (
              <div>
                <div className="text-[12px] text-subtle">{t("Calculation")}</div>
                <div className="num mt-0.5 rounded-md bg-paper px-3 py-2 font-mono text-[12px] text-ink">
                  {atom.formula}
                </div>
              </div>
            )}
            {atom.note && <p className="rounded-md bg-amber-50 px-3 py-2 text-[12.5px] text-amber-700">{atom.note}</p>}
            {children.length > 0 && (
              <div>
                <div className="text-[12px] text-subtle">{t("Linked items (shown, not added)")}</div>
                <ul className="mt-1 space-y-1">
                  {children.map((c) => (
                    <li key={c.id} className="flex justify-between gap-2 text-[12.5px]">
                      <span className="text-muted">{c.fee_label}</span>
                      <span className="num">{chf(c.amount, 2)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {atom.evidence_sources && atom.evidence_sources.length > 0 && (
              <div>
                <div className="text-[12px] text-subtle">{t("Sources")}</div>
                <ul className="mt-1 space-y-1">
                  {atom.evidence_sources.map((s, i) => (
                    <li key={s}>
                      <button
                        type="button"
                        className={i === idx ? "font-medium text-teal-700" : "text-muted hover:text-ink"}
                        onClick={() => setIdx(i)}
                      >
                        {s}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {docId.data && (
              <Link to={`/p/${pid}/review?doc=${docId.data.doc.id}&fact=${factId}`}>
                <Button variant="outline" size="sm">
                  <ExternalLink className="h-3.5 w-3.5" /> {t("Open in evidence review")}
                </Button>
              </Link>
            )}
          </div>
          <div className="h-[460px] overflow-hidden rounded-md border border-line">
            {!factIds.length ? (
              <div className="flex h-full items-center justify-center p-6 text-center text-[13px] text-muted">
                {atom.measurement === "unknown"
                  ? t("No document contains this cost yet. See the document request list for what would resolve it.")
                  : t("This value comes from proposal inputs, not from a client document.")}
              </div>
            ) : docId.isLoading || !docId.data ? (
              <Spinner label={t("Locating source")} />
            ) : docId.data.doc.filename.endsWith(".xlsx") ? (
              <SheetEvidence docId={docId.data.doc.id} facts={docId.data.facts} activeId={factId} />
            ) : (
              <PdfEvidence
                docId={docId.data.doc.id}
                facts={docId.data.facts}
                activeId={factId}
                page={docId.data.fact.evidence.page ?? 1}
                compact
              />
            )}
          </div>
        </div>
      )}
    </Dialog>
  );
}
