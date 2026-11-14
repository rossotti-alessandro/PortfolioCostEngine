/** Firm tariff (SC-7.6): the firm's own prices, entered once; every new cost review starts from them. */
import { TariffFields } from "@/components/ProposalForm";
import { PageTitle } from "@/components/Shell";
import { Button, Card, CardHeader, ErrorBox, Spinner } from "@/components/ui";
import { api, getRole } from "@/lib/api";
import { t } from "@/lib/i18n";
import type { ProposalConfig } from "@/lib/types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

export default function FirmTariffPage() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["firm-tariff"], queryFn: api.firmTariff });
  const [cfg, setCfg] = useState<ProposalConfig | null>(null);
  useEffect(() => {
    if (q.data) setCfg(q.data.config);
  }, [q.data]);
  const save = useMutation({
    mutationFn: (c: ProposalConfig) => api.saveFirmTariff(c),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["firm-tariff"] }),
  });
  if (q.error) return <ErrorBox error={q.error} />;
  if (!cfg || !q.data) return <Spinner />;
  const senior = getRole() === "senior";
  const dirty = JSON.stringify(cfg) !== JSON.stringify(q.data.config);
  const set = (k: keyof ProposalConfig, v: unknown) => setCfg({ ...cfg, [k]: v });
  return (
    <div className="mx-auto max-w-[1100px] px-6 py-6">
      <PageTitle
        title={t("Firm tariff")}
        subtitle={t(
          "Your own prices. Every new cost review starts from them; one review can still be adjusted on its Compare page.",
        )}
      />
      {!q.data.saved && (
        <div className="mb-4 rounded-[var(--radius-card)] border border-amber-300 bg-amber-50 px-4 py-3 text-[13px] text-amber-900">
          {t("Not set yet: new cost reviews use the synthetic demo tariff until a senior saves your prices here.")}
        </div>
      )}
      <Card>
        <CardHeader
          title={t("Your prices")}
          subtitle={t("Fee bands, custody, trading, FX margin and VAT, as you would charge this client.")}
          actions={
            <Button
              variant="primary"
              size="sm"
              disabled={!senior || !dirty}
              loading={save.isPending}
              onClick={() => save.mutate(cfg)}
            >
              {t("Save firm tariff")}
            </Button>
          }
        />
        {save.error && <ErrorBox error={save.error} />}
        <p className="px-5 pt-4 text-[12.5px] text-muted">
          {q.data.saved &&
            `${t("Last saved by")} ${q.data.updated_by} · ${(q.data.updated_at ?? "").slice(0, 16).replace("T", " ")}. `}
          {!senior && t("Only a senior reviewer can change it.")}
        </p>
        <fieldset disabled={!senior} className="p-5">
          <TariffFields cfg={cfg} set={set} firmWide />
        </fieldset>
      </Card>
    </div>
  );
}
