/** The firm's prices: fee bands, custody, trading, FX and VAT. Used per prospect (Compare) and firm-wide (Firm tariff). */
import { Button, Field, inputCls } from "@/components/ui";
import { cn } from "@/lib/format";
import { t } from "@/lib/i18n";
import type { ProposalConfig } from "@/lib/types";
import { Plus, Trash2 } from "lucide-react";

export const NUM_FIELDS: { k: keyof ProposalConfig; label: string; hint?: string }[] = [
  { k: "custody_bps", label: "Custody fee (bps p.a.)", hint: "Partner custodian, on securities" },
  { k: "custody_min", label: "Custody minimum (CHF p.a.)" },
  { k: "brokerage_bps", label: "Brokerage (bps of turnover)" },
  { k: "fx_bps", label: "FX margin (bps of FX volume)" },
  { k: "annual_turnover_chf", label: "Annual turnover (CHF)", hint: "Same volume assumed today and in the proposal" },
  { k: "fx_notional_chf", label: "Annual FX volume (CHF)" },
  { k: "vat_pct", label: "VAT (%)", hint: "Applied only when the client is domiciled in CH" },
];

// Turnover and FX volume are estimates about one prospect, not firm prices.
export const PROSPECT_ONLY: (keyof ProposalConfig)[] = ["annual_turnover_chf", "fx_notional_chf"];

export function TariffFields({
  cfg,
  set,
  firmWide = false,
}: {
  cfg: ProposalConfig;
  set: (k: keyof ProposalConfig, v: unknown) => void;
  firmWide?: boolean;
}) {
  const fields = firmWide ? NUM_FIELDS.filter((f) => !PROSPECT_ONLY.includes(f.k)) : NUM_FIELDS;
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <div className="space-y-3">
        <Field label={t("Firm name (shown to the client)")}>
          <input className={inputCls} value={cfg.firm_name} onChange={(e) => set("firm_name", e.target.value)} />
        </Field>
        <Field label={t("Custodian")}>
          <input className={inputCls} value={cfg.custodian} onChange={(e) => set("custodian", e.target.value)} />
        </Field>
        <div>
          <div className="flex items-center justify-between">
            <span className="text-[12.5px] font-medium">{t("Management fee tiers")}</span>
            <select
              className="h-7 rounded border border-line-strong bg-surface px-1.5 text-[12px]"
              value={cfg.eam_tier_method}
              onChange={(e) => set("eam_tier_method", e.target.value)}
              aria-label={t("Tier method")}
            >
              <option value="marginal">{t("Marginal (each band at its rate)")}</option>
              <option value="whole_base">{t("Whole base (one rate for all)")}</option>
            </select>
          </div>
          <div className="mt-1.5 space-y-1.5">
            {cfg.eam_tiers.map(([up, rate], i) => (
              <div key={`${i}-${up}`} className="flex items-center gap-2 text-[12.5px]">
                <span className="w-12 text-muted">{i === 0 ? t("Up to") : up === null ? t("Above") : t("Up to")}</span>
                <input
                  className={cn(inputCls, "h-8")}
                  placeholder={t("no limit")}
                  value={up ?? ""}
                  aria-label={t("Band upper limit CHF")}
                  onChange={(e) =>
                    set(
                      "eam_tiers",
                      cfg.eam_tiers.map((t, j) =>
                        j === i ? [e.target.value === "" ? null : e.target.value, t[1]] : t,
                      ),
                    )
                  }
                />
                <input
                  className={cn(inputCls, "h-8 w-24")}
                  value={rate}
                  aria-label={t("Rate bps")}
                  onChange={(e) =>
                    set(
                      "eam_tiers",
                      cfg.eam_tiers.map((t, j) => (j === i ? [t[0], e.target.value] : t)),
                    )
                  }
                />
                <span className="text-muted">bps</span>
                {cfg.eam_tiers.length > 1 && (
                  <button
                    type="button"
                    aria-label={t("Remove band")}
                    className="text-subtle hover:text-red-700"
                    onClick={() =>
                      set(
                        "eam_tiers",
                        cfg.eam_tiers.filter((_, j) => j !== i),
                      )
                    }
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                )}
              </div>
            ))}
            <Button
              variant="ghost"
              size="sm"
              onClick={() =>
                set("eam_tiers", [...cfg.eam_tiers.slice(0, -1), ["", cfg.eam_tiers.at(-1)?.[1] ?? "50"], [null, "40"]])
              }
            >
              <Plus className="h-3.5 w-3.5" /> {t("Add band")}
            </Button>
          </div>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        {fields.map((f) => (
          <Field key={f.k} label={t(f.label)} hint={f.hint && t(f.hint)}>
            <input
              className={inputCls}
              inputMode="decimal"
              value={String(cfg[f.k])}
              onChange={(e) => set(f.k, e.target.value)}
            />
          </Field>
        ))}
      </div>
    </div>
  );
}
