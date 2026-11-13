import { t } from "@/lib/i18n";
import type { Analysis } from "@/lib/types";
import { CheckCircle2, FileSearch, FileText } from "lucide-react";
import { Link } from "react-router-dom";
import { Button, Card, Empty } from "./ui";

/**
 * One honest line on what the figures rest on: how many values were read from the documents,
 * how many a person has checked, and how many review points are open. Automatic reading is partial
 * on real bank documents, so this stays visible next to every result.
 */
export function ReadSummary({ a }: { a: Analysis }) {
  const checked = a.review.reviewed + a.review.rejected;
  // Unknown costs are listed once, as documents to ask for, so they are not counted again as points.
  const open = a.review_points.filter((p) => !(a.requests.length && p.kind === "not_determined")).length;
  const ask = a.requests.filter((r) => r.status === "open").length;
  const all = a.review.facts > 0 && checked >= a.review.facts;
  return (
    <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[12.5px] text-muted" data-testid="read-summary">
      {all ? (
        <CheckCircle2 className="h-4 w-4 text-teal-700" aria-hidden />
      ) : (
        <FileSearch className="h-4 w-4 text-amber-700" aria-hidden />
      )}
      <span>{t("{facts} values read from {docs} documents", { facts: a.review.facts, docs: a.documents.length })}</span>
      <span aria-hidden>·</span>
      <span className={all ? "text-teal-700" : "text-amber-700"}>{t("{n} checked by a person", { n: checked })}</span>
      <span aria-hidden>·</span>
      <span>{t("{n} points to review", { n: open })}</span>
      {ask > 0 && (
        <>
          <span aria-hidden>·</span>
          <span>{t("{n} documents to ask for", { n: ask })}</span>
        </>
      )}
    </p>
  );
}

/**
 * No holdings valued yet, so there is nothing to put costs in proportion to and no total is shown at all.
 * Either no statement of assets was uploaded, or its positions could not be valued in CHF (a currency
 * without a rate on the documents, say): the second case points to the checks instead of asking for
 * a statement that is already there.
 */
export function NotStarted({ pid, docs }: { pid: number; docs: { doc_type: string }[] }) {
  const statements = docs.filter((d) => d.doc_type === "portfolio_statement").length;
  return (
    <Card>
      <Empty icon={<FileText className="h-8 w-8" />} title={t("Costs are not calculated yet")}>
        <p className="mx-auto max-w-[520px]">
          {statements
            ? t(
                statements === 1
                  ? "A statement of assets is uploaded, but none of its positions could be valued in CHF, for example because a currency has no exchange rate on the documents. “Validation and reconciliation” on the Costs page says why. No total is shown (not zero)."
                  : "{n} statements of assets are uploaded, but none of their positions could be valued in CHF, for example because a currency has no exchange rate on the documents. “Validation and reconciliation” on the Costs page says why. No total is shown (not zero).",
                { n: statements },
              )
            : docs.length
              ? t(
                  "None of the {n} documents is a statement of assets. Without the positions no cost can be put in proportion to assets, so no total is shown (not zero).",
                  { n: docs.length },
                )
              : t("Upload a statement of assets for each bank to start.")}
        </p>
        <Link to={`/p/${pid}/documents`} className="mt-3 inline-block">
          <Button>{t("Upload documents")}</Button>
        </Link>
      </Empty>
    </Card>
  );
}
