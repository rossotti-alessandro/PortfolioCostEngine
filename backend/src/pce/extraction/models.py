"""Typed extraction contracts. The LLM/VLM path (when added) must emit these same models;
nothing writes into the cost ledger without passing validation here."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class DocType(StrEnum):
    PORTFOLIO_STATEMENT = "portfolio_statement"
    COST_REPORT = "cost_report"
    CASH_STATEMENT = "cash_statement"
    TARIFF = "tariff"
    KID = "kid"
    TERMSHEET = "termsheet"
    UNKNOWN = "unknown"


DOC_TYPE_LABELS = {
    DocType.PORTFOLIO_STATEMENT: "Statement of assets / holdings",
    DocType.COST_REPORT: "Annual costs & charges report",
    DocType.CASH_STATEMENT: "Cash account statement",
    DocType.TARIFF: "Price schedule / fee agreement",
    DocType.KID: "Key Information Document (KID)",
    DocType.TERMSHEET: "Structured product termsheet",
    DocType.UNKNOWN: "Unclassified — needs review",
}


class Evidence(BaseModel):
    page: int | None = None  # 1-based, PDF
    bbox: list[float] | None = None  # [x0, y0, x1, y1] PDF points, top-left origin
    page_width: float | None = None
    page_height: float | None = None
    sheet: str | None = None  # spreadsheet
    cell: str | None = None  # e.g. "H8"
    snippet: str = ""
    engine: str = ""
    confidence: float = 1.0
    # Provenance for the evidence viewer (SC-5.8): where the label sits, the whole row, and the layout region.
    label_bbox: list[float] | None = None
    row_bbox: list[float] | None = None
    region: str | None = None  # table | text | header | footnote


class Check(BaseModel):
    name: str  # e.g. "second_reader_agrees", "components_sum_to_total"
    passed: bool
    detail: str = ""


class Review(BaseModel):
    """Why a value can or cannot enter the totals without an analyst looking at it."""

    status: str = "accepted"  # accepted | needs_review
    reasons: list[str] = Field(default_factory=list)  # short codes, e.g. "engines_disagree"
    engines: list[str] = Field(default_factory=list)  # readers that read the same value
    alternatives: list[dict] = Field(default_factory=list)  # {value, engine, bbox} read differently
    checks: list[Check] = Field(default_factory=list)


class Fact(BaseModel):
    """One extracted value with provenance. ``value`` is a decimal string, never a float."""

    key: str  # stable within a document, e.g. "position:ZZGEQLDRA013"
    kind: str  # position | doc_total | fee_observed | cash_debit | fee_rule | product_cost | reported | meta
    field: str
    label: str
    value: str | None = None
    currency: str | None = None
    isin: str | None = None
    fee_code: str | None = None
    measurement: str | None = None
    extra: dict = Field(default_factory=dict)
    evidence: Evidence
    review: Review | None = None


class DocumentProfile(BaseModel):
    doc_type: DocType
    type_score: float
    institution: str | None = None
    jurisdiction: str | None = None
    language: str | None = None
    as_of: str | None = None  # ISO date
    period_start: str | None = None
    period_end: str | None = None
    currency: str | None = None
    page_count: int = 0
    engines: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    timings_ms: dict[str, int] = Field(default_factory=dict)  # per pipeline stage, shown to the analyst
    # Cost-looking lines (fee word + rate or amount) that produced no value: the analyst's recall check.
    possible_misses: list[dict] = Field(default_factory=list)


class ExtractionResult(BaseModel):
    profile: DocumentProfile
    facts: list[Fact]
    extractor_version: str
