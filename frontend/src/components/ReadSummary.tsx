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
  const open = a.review_points.length;
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
    </p>
  );
}

/** No statement of assets yet: there is nothing to put costs in proportion to, so no total is shown at all. */
export function NotStarted({ pid, docs }: { pid: number; docs: number }) {
  return (
    <Card>
      <Empty icon={<FileText className="h-8 w-8" />} title={t("Costs are not calculated yet")}>
        <p className="mx-auto max-w-[520px]">
          {docs
            ? t(
                "None of the {n} documents is a statement of assets. Without the positions no cost can be put in proportion to assets, so no total is shown (not zero).",
                { n: docs },
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
