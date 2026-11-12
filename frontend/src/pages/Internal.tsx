import { PageTitle } from "@/components/Shell";
import { Badge, Card, CardHeader, Empty, ErrorBox, Kpi, Spinner, StatGrid } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { BOUND_TEXT, chf } from "@/lib/format";
import { t } from "@/lib/i18n";
import { useQuery } from "@tanstack/react-query";
import { Lock } from "lucide-react";
import { useParams } from "react-router-dom";

const VERDICT: Record<string, { label: string; tone: string; text: string }> = {
  insufficient_evidence: {
    label: "Insufficient evidence",
    tone: "amber",
    text: "Close the open document requests before deciding: the saving is only a lower bound.",
  },
  no_client_benefit: {
    label: "No client benefit",
    tone: "red",
    text: "The proposal does not cost the client less. Do not pitch on cost.",
  },
  below_margin_threshold: {
    label: "Below margin threshold",
    tone: "red",
    text: "The client saves, but the mandate does not meet the firm's minimum margin.",
  },
  proceed_to_senior_review: {
    label: "Proceed to senior review",
    tone: "green",
    text: "Client saves and the mandate meets the firm's margin threshold.",
  },
};

/** Firm-only view. The API refuses it to analysts (403) and never includes it in client payloads. */
export default function InternalPage() {
  const pid = Number(useParams().id);
  const q = useQuery({ queryKey: ["internal", pid], queryFn: () => api.internal(pid), retry: false });
  if (q.isLoading) return <Spinner />;
  if (q.error instanceof ApiError && q.error.status === 403)
    return (
      <Card>
        <Empty
          icon={<Lock className="h-6 w-6" />}
          title={t("Restricted to senior reviewers and relationship managers")}
        >
          {t(
            "Internal revenue and margin are never shown to analysts or included in client documents. Switch the demo role in the sidebar to view.",
          )}
        </Empty>
      </Card>
    );
  if (q.error || !q.data) return <ErrorBox error={q.error ?? "no data"} />;
  const { internal: i, same_holdings: s } = q.data;
  const v = VERDICT[i.verdict] ?? { label: i.verdict, tone: "grey", text: "" };
  return (
    <div className="space-y-4">
      <PageTitle
        title={t("Internal economics")}
        subtitle={t(
          "Is this mandate worth it for the firm, and is it good for the client? Visible only to senior reviewers and relationship managers.",
        )}
        actions={
          <Badge tone="violet">
            <Lock className="h-3 w-3" /> {t("Internal only, never client-facing")}
          </Badge>
        }
      />
      <StatGrid>
        <Kpi label={t("Annual fee revenue")} value={chf(i.annual_revenue)} sub={t("Management fee, before VAT")} />
        <Kpi
          label={t("Servicing cost")}
          value={chf(i.annual_servicing_cost)}
          sub={t("Onboarding {amount} one-off", { amount: chf(i.onboarding_one_off) })}
        />
        <Kpi
          label={t("Annual contribution")}
          value={chf(i.annual_contribution)}
          sub={i.margin_pct ? t("Margin {pct}%", { pct: Number(i.margin_pct).toFixed(1) }) : undefined}
          tone="navy"
        />
        <Kpi
          label={t("Client saving")}
          value={`${t(BOUND_TEXT[s.bound])} ${chf(s.annual_saving)}`}
          tone="teal"
          sub={q.data.current_complete ? t("Complete evidence") : t("Lower bound: costs still unknown")}
        />
      </StatGrid>
      <Card>
        <CardHeader title={t("Decision")} actions={<Badge tone={v.tone}>{t(v.label)}</Badge>} />
        <div className="space-y-2 p-5 text-[13.5px]">
          <p className="font-medium text-ink">{v.text && t(v.text)}</p>
          <ul className="list-disc space-y-1 pl-5 text-muted">
            {i.reasons.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
          <p className="pt-1 text-[12.5px] text-subtle">
            {t("First-year contribution after onboarding: {amount}. Minimum margin set in proposal inputs: {pct}%.", {
              amount: chf(i.first_year_contribution),
              pct: q.data.proposal_inputs.internal.min_margin_pct,
            })}
          </p>
        </div>
      </Card>
    </div>
  );
}
