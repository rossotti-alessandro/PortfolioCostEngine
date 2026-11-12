export type Measurement =
  | "observed"
  | "contractual"
  | "public_tariff"
  | "estimated"
  | "illustrative"
  | "maximum"
  | "unknown"
  | "not_applicable";

export type Role =
  | "counted"
  | "included_in_parent"
  | "corroborating"
  | "unknown"
  | "not_applicable"
  | "not_a_paid_cost"
  | "one_off";

export interface Evidence {
  page: number | null;
  bbox: number[] | null;
  page_width: number | null;
  page_height: number | null;
  sheet: string | null;
  cell: string | null;
  snippet: string;
  engine: string;
  confidence: number;
}

export interface Fact {
  id: number;
  document_id: number;
  key: string;
  kind: string;
  field: string;
  label: string;
  value: string | null;
  value_extracted: string | null;
  currency: string | null;
  isin: string | null;
  fee_code: string | null;
  fee_label: string | null;
  measurement: string | null;
  extra: Record<string, unknown>;
  evidence: Evidence;
  status: "extracted" | "accepted" | "corrected" | "rejected" | "manual";
}

export interface DocumentRow {
  id: number;
  filename: string;
  sha256: string;
  size: number;
  media_type: string;
  doc_type: string;
  doc_type_label: string;
  detected_type: string;
  profile: {
    institution: string | null;
    jurisdiction: string | null;
    language: string | null;
    as_of: string | null;
    period_start: string | null;
    period_end: string | null;
    currency: string | null;
    engines: string[];
    warnings: string[];
    page_count: number;
  };
  pages: { number: number; width: number; height: number; engine: string }[];
  status: string;
  uploaded_at: string;
  uploaded_by: string;
  fact_count: number;
}

/** One input of a computed number, with where it was read (inline from the analysis payload). */
/** What the extraction's own checks said about a value (fact.extra.review, SC-5.8 / SC-5.14). */
export interface ExtractionReview {
  status: string; // accepted | needs_review
  reasons?: string[];
  engines?: string[];
  checks?: { name: string; passed: boolean; detail?: string }[];
  alternatives?: { value?: string | null; engine?: string }[];
}

export interface EvidenceRef {
  fact_id: number;
  role: "value" | "basis" | "fx_rate";
  document_id: number;
  filename: string;
  where: string;
  field: string;
  label: string;
  value: string | null;
  value_extracted: string | null;
  currency: string | null;
  status: Fact["status"];
  review: ExtractionReview | null;
  page: number | null;
  bbox: number[] | null;
  sheet: string | null;
  cell: string | null;
  snippet: string | null;
  engine: string | null;
  confidence: number | null;
}

export interface ReviewPoint {
  key: string;
  kind:
    | "not_determined"
    | "low_confidence"
    | "extraction_flag"
    | "corrected"
    | "unreviewed"
    | "list_price"
    | "rate_high"
    | "large_driver"
    | "check";
  severity: "high" | "medium" | "low";
  atom_id: string | null;
  fact_ids: number[];
  amount: string | null;
  vars: Record<string, string>;
}

export interface Atom {
  id: string;
  fee_code: string;
  fee_label: string;
  layer: string;
  label: string;
  institution: string | null;
  instrument_id: string | null;
  amount: string | null;
  bps: string | null;
  measurement: Measurement;
  incidence: string;
  recurring: boolean;
  included_in: string | null;
  corroborates: string | null;
  role: Role | null;
  rate_bps: string | null;
  basis_amount: string | null;
  evidence_fact_ids: number[];
  evidence_sources?: string[];
  evidence?: EvidenceRef[];
  formula: string;
  note: string;
  materiality: string;
}

export interface Ledger {
  total_known: string;
  billed_known: string;
  embedded_known: string;
  one_off_known: string;
  total_bps: string | null;
  scope_aum: string | null;
  is_complete: boolean;
  verified_share: string | null;
  by_measurement: Record<string, string>;
  by_layer: Record<string, string>;
  by_institution: Record<string, string>;
  by_instrument: Record<string, string>;
  unknown: string[];
  warnings: string[];
  atoms: Atom[];
}

export interface Comparison {
  current_known: string;
  proposal_known: string;
  annual_saving: string;
  annual_saving_bps: string | null;
  bound: "point" | "at_least" | "at_most" | "indeterminate";
  migration_one_off: string;
  first_year_net: string;
  payback_months: string | null;
  like_for_like: boolean;
  caveats: string[];
}

export interface Check {
  key: string;
  title: string;
  status: "pass" | "warn" | "fail" | "info";
  detail: string;
  fact_ids: number[];
  sources?: string[];
  evidence?: EvidenceRef[];
}

export interface MissingRequest {
  key: string;
  priority: number;
  institution: string | null;
  title: string;
  ask_for: string;
  reason: string;
  blocks: string[];
  assets_affected: string;
  document_type: string;
  status: "open" | "sent" | "waived";
}

export interface Holding {
  fact_id: number;
  document_id: number;
  institution: string;
  isin: string | null;
  name: string;
  asset_class: string;
  asset_class_inferred: boolean;
  value: string;
  currency: string;
  synthetic_isin: boolean;
  weight_pct: string | null;
}

export interface ProposalConfig {
  firm_name: string;
  custodian: string;
  eam_tiers: [string | null, string][];
  eam_tier_method: "marginal" | "whole_base";
  vat_pct: string;
  custody_bps: string;
  custody_min: string;
  brokerage_bps: string;
  fx_bps: string;
  annual_turnover_chf: string;
  fx_notional_chf: string;
  migration: Record<string, string>;
  internal: { servicing_cost: string; onboarding_cost: string; min_margin_pct: string };
  optimized_swaps: { from: string; to: string; to_name: string; to_ongoing: string; to_transaction: string }[];
}

export interface Analysis {
  engine_version: string;
  synthetic: boolean;
  prospect: { id: number; code: string; label: string; domicile: string; synthetic: boolean };
  aum: { total: string; cash: string; custody_eligible: string; by_institution: Record<string, string> };
  institutions: {
    name: string;
    legal_name: string | null;
    jurisdiction: string | null;
    as_of: string | null;
    assets: string;
    documents: number[];
  }[];
  holdings: Holding[];
  current: Ledger;
  coverage: { institution: string; assets: string; jurisdiction: string | null; cells: Record<string, string> }[];
  checks: Check[];
  review_points: ReviewPoint[];
  requests: MissingRequest[];
  comparison_exclusions: { fee_code: string; label: string; amount: string; reason: string }[];
  scenarios: {
    current_comparable: Ledger;
    same_holdings: { ledger: Ledger; comparison: Comparison; migration_items: Record<string, string> };
    optimized: {
      ledger: Ledger;
      comparison: Comparison;
      swaps: {
        from: string;
        from_name: string;
        to: string;
        to_name: string;
        value: string;
        from_rate_pct: string | null;
        to_rate_pct: string;
      }[];
      rebuild_trading_cost: string;
    };
  };
  proposal_inputs: ProposalConfig;
  client_domicile: string;
  review: { facts: number; reviewed: number; rejected: number };
  snapshot_hash: string;
  approval: { user: string; role: string; at: string; note: string; valid: boolean } | null;
  documents: { id: number; filename: string; doc_type: string }[];
}

export interface InternalView {
  internal: {
    annual_revenue: string;
    annual_servicing_cost: string;
    onboarding_one_off: string;
    annual_contribution: string;
    first_year_contribution: string;
    margin_pct: string | null;
    verdict: string;
    reasons: string[];
  };
  same_holdings: Comparison;
  current_complete: boolean;
  requests: MissingRequest[];
  proposal_inputs: ProposalConfig;
  synthetic: boolean;
}

export interface ProspectRow {
  id: number;
  code: string;
  label: string;
  domicile: string;
  synthetic: boolean;
  created_at: string;
  documents: number;
  summary: {
    aum: string;
    current_known: string;
    current_bps: string | null;
    complete: boolean;
    open_requests: number;
    saving: string;
    bound: string;
    approved: boolean;
  } | null;
}

export interface DocTypeRow {
  family: string;
  document_type: string;
  label_en: string;
  label_it: string;
  label_de: string;
  priority: string;
  extract_targets: string;
  proves: string;
  cannot_prove: string;
  typical_source: string;
  parser: boolean;
}

export interface FeeRow {
  layer: string;
  fee_code: string;
  label_en: string;
  label_it: string;
  basis: string;
  recurrence: string;
  economic_incidence: string;
  default_status: string;
  parent_or_overlap: string;
  in_default_comparison: string;
  primary_evidence: string;
}

export interface PublicSourceRow {
  source_id: string;
  issuer: string;
  document: string;
  document_type: string;
  jurisdiction: string;
  valid_from: string;
  url: string;
  page: string;
  fee_code: string;
  figure: string;
  status: string;
  note: string;
}

export interface Taxonomy {
  document_types: DocTypeRow[];
  fees: FeeRow[];
  public_sources: PublicSourceRow[];
}

export type StageStatus = "ok" | "warn" | "fail" | "skipped";
export interface PipelineStage {
  key: string;
  status: StageStatus;
  summary: string;
  vars: Record<string, string | number>;
  ms: number | null;
  details: { label: string; value: string }[];
  warnings?: string[];
  warning_vars?: Record<string, string | number>;
  looked_for?: { label: string; found: boolean }[];
  misses?: { page: number; bbox: number[]; text: string; fee_code: string }[];
  values?: {
    id: number;
    label: string;
    engine: string;
    confidence: number | null;
    value: string | null;
    currency: string | null;
    where: string;
    status: string;
  }[];
  checks?: { title: string; status: string; detail: string }[];
  atoms?: {
    label: string;
    fee_label: string;
    layer: string;
    measurement: string;
    role: string;
    amount: string | null;
    formula: string;
  }[];
}
export interface DocumentPipeline {
  document: { id: number; filename: string; doc_type: string; prospect_id: number };
  extractor_version: string;
  total_ms: number | null;
  stages: PipelineStage[];
}
