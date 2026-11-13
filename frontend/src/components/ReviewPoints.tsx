import { chf, cn } from "@/lib/format";
import { t, tm } from "@/lib/i18n";
import { reasonText } from "@/lib/trail";
import type { ReviewPoint } from "@/lib/types";
import { AlertTriangle, Info, OctagonAlert } from "lucide-react";
import { useState } from "react";
import { Badge, Card, CardHeader } from "./ui";

const SEVERITY = {
  high: { label: "Check first", Icon: OctagonAlert, cls: "text-red-700" },
  medium: { label: "Check", Icon: AlertTriangle, cls: "text-amber-700" },
  low: { label: "Note", Icon: Info, cls: "text-navy-700" },
} as const;

/** Wording lives here so it can be translated; the server sends the kind and its variables. */
function text(p: ReviewPoint): { title: string; detail: string } {
  const v = { ...p.vars };
  if (v.confidence) v.confidence = `${Math.round(Number(v.confidence) * 100)}%`;
  switch (p.kind) {
    case "not_determined":
      return {
        title: t("Not determined: {label}", v),
        detail: t("No document shows this cost yet. It is not counted as zero; see what is missing."),
      };
    case "low_confidence":
      return {
        title: t("Low reading confidence: {label}", v),
        detail: t("The value was read with {confidence} confidence. Compare it with the page.", v),
      };
    case "extraction_flag":
      return {
        title: t("Flagged at extraction: {label}", v),
        detail: t("Reasons: {reasons}.", { reasons: (v.reasons ?? "").split(",").map(reasonText).join("; ") }),
      };
    case "unused_mentions":
      return {
        title: t("{n} fee amounts in {file} are not used in any total", v),
        detail: t(
          "Found on the page but not matched to a cost. Open them, then accept or reject each in evidence review.",
        ),
      };
    case "corrected":
      return { title: t("Corrected by an analyst: {label}", v), detail: t("Read as {old}, now {new}.", v) };
    case "unreviewed":
      return {
        title: t("Not yet checked: {label}", v),
        detail: t("{share}% of the known cost rests on a value nobody has compared with the page yet.", v),
      };
    case "list_price":
      return {
        title: t("List price, not the client's rate: {label}", v),
        detail: t("Based on the bank's public price list. Ask for the client's fee agreement or a fee statement."),
      };
    case "rate_high":
      return {
        title: t("Unusually high rate: {label}", v),
        detail: t(
          "{bps} bps is above the {limit} bps review threshold for this kind of fee. Check the basis and the page.",
          v,
        ),
      };
    case "large_driver":
      return {
        title: t("Largest single cost: {label}", v),
        detail: t("{share}% of the known cost. Worth a second look before it goes to the client.", v),
      };
    default:
      return { title: tm(v.title ?? ""), detail: tm(v.detail ?? "") };
  }
}

export function ReviewPoints({ points, onOpen }: { points: ReviewPoint[]; onOpen: (p: ReviewPoint) => void }) {
  const [all, setAll] = useState(false);
  if (!points.length) return null;
  const n = { high: 0, medium: 0, low: 0 };
  for (const p of points) n[p.severity]++;
  const shown = all ? points : points.slice(0, 5);
  return (
    <Card>
      <CardHeader
        title={t("Points to review")}
        subtitle={t(
          "What an analyst should check before this goes to a client. Click a point to see the number and its source.",
        )}
        actions={
          <div className="flex gap-1.5">
            {n.high > 0 && <Badge tone="red">{t("{n} check first", { n: n.high })}</Badge>}
            {n.medium > 0 && <Badge tone="amber">{t("{n} to check", { n: n.medium })}</Badge>}
            {n.low > 0 && <Badge>{t("{n} notes", { n: n.low })}</Badge>}
          </div>
        }
      />
      <ul className="divide-y divide-line">
        {shown.map((p) => {
          const s = SEVERITY[p.severity];
          const { title, detail } = text(p);
          return (
            <li key={p.key}>
              <button
                type="button"
                onClick={() => onOpen(p)}
                className="flex w-full gap-3 px-5 py-2.5 text-left text-[13px] hover:bg-teal-50 focus:bg-teal-50 focus:outline-none"
              >
                <s.Icon className={cn("mt-0.5 h-4 w-4 shrink-0", s.cls)} aria-label={t(s.label)} />
                <span className="min-w-0 flex-1">
                  <span className="block font-medium text-ink">{title}</span>
                  <span className="block text-muted">{detail}</span>
                </span>
                {p.amount && <span className="num shrink-0 text-muted">{chf(p.amount)}</span>}
              </button>
            </li>
          );
        })}
      </ul>
      {points.length > 5 && (
        <button
          type="button"
          onClick={() => setAll(!all)}
          className="w-full border-t border-line px-5 py-2 text-left text-[12.5px] font-medium text-teal-700 hover:bg-paper"
        >
          {all ? t("Show fewer") : t("Show all {n} points", { n: points.length })}
        </button>
      )}
    </Card>
  );
}
