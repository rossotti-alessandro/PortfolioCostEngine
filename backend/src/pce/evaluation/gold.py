"""Golden labels: what is printed on each document, and what the portfolio numbers must be.

Three sources, one shape (``GoldDoc``):
- SYNTHETIC prospects P-1042 and P-2077: labels built from the generator's own inputs (``demo.spec``,
  ``demo.archetypes``), never from parser output, so they are independent of every strategy. Exhaustive:
  every value-bearing fact is labelled, so precision is defined. Portfolio numbers are pinned by hand.
- The OCR benchmark pages (``data/specimens/ocrbench/groundtruth.json``): 514 hand-checked fee figures
  on public PDFs, exhaustive for fee figures on each page.
- Manifest ``expected`` columns (``data/reference/*_corpus.csv``): a few values a human read; recall only.
Real PDFs are third-party copyright and are fetched on demand into ``var/``; missing files are skipped.
"""

from __future__ import annotations

import csv
import json
from decimal import Decimal
from pathlib import Path

from pydantic import BaseModel, Field

from ..demo import archetypes as A
from ..demo import spec as S
from .metrics import GoldItem

ROOT = Path(__file__).resolve().parents[4]
OCRBENCH_GT = ROOT / "data" / "specimens" / "ocrbench" / "groundtruth.json"
SPECIMENS = ROOT / "data" / "reference" / "specimen_corpus.csv"
SPECIMEN_FILES = ROOT / "var" / "specimens"

# Fact kinds that are fee figures: the scope of precision on real pages, where only fees are labelled.
FEE_KINDS = {"fee_observed", "cash_debit", "fee_rule", "product_cost", "reported"}


class GoldDoc(BaseModel):
    file: str
    doc_type: str | None = None  # pipeline DocType value; None = not labelled
    items: list[GoldItem] = Field(default_factory=list)
    exhaustive: bool = True  # every value in scope is labelled -> precision is defined
    pages: list[int] | None = None  # only facts on these pages are in scope (benchmark pages)
    kinds: set[str] | None = None  # only facts of these kinds are in scope


class GoldPortfolio(BaseModel):
    """Expected analysis output: dotted path into ``analyse()`` -> value (Decimal string or bool)."""

    expect: dict[str, str | bool]
    requests: list[str] = Field(default_factory=list)  # request keys that must be raised
    failed_checks: list[str] = Field(default_factory=list)  # check keys that must fail


class Corpus(BaseModel):
    name: str
    folder: Path
    docs: list[GoldDoc]
    portfolio: GoldPortfolio | None = None
    domicile: str = "CH"


def _d(x: Decimal) -> str:
    return str(x)


def _doc(file: str, doc_type: str, pairs: list[tuple[str, Decimal | str | None]]) -> GoldDoc:
    return GoldDoc(
        file=file,
        doc_type=doc_type,
        items=[GoldItem(file=file, key=k, value=None if v is None else str(v)) for k, v in pairs],
    )


def _kid(file: str, k: dict, mgmt_key: str = "mgmt_included") -> GoldDoc:
    illus = (Decimal(10000) * (k["ongoing"] + k["transaction"]) / 100).quantize(Decimal("1"))
    pairs: list[tuple[str, Decimal | str | None]] = [
        ("kid:illustration_1y", illus),
        ("kid:FUND_ENTRY_CHARGE", k["entry_max"]),
        ("kid:FUND_EXIT_CHARGE", k.get("exit", Decimal("0.00"))),
        ("kid:FUND_ONGOING", k["ongoing"]),
        ("kid:FUND_TRANSACTION", k["transaction"]),
        ("kid:FUND_PERFORMANCE", k.get("performance", Decimal("0.00"))),
    ]
    if k.get(mgmt_key) is not None:
        pairs.append(("kid:FUND_MGMT_FEE", k[mgmt_key]))
    return _doc(file, "kid", pairs)


def _positions(rows: list[tuple[str, Decimal]], total: Decimal) -> list[tuple[str, Decimal | str | None]]:
    return [*rows, ("total:assets", total)]


def synthetic_p1042(folder: Path) -> Corpus:
    alpha_pos = [
        (f"position:{p.isin}" if p.isin else f"position:cash:{p.name}", p.value_chf)
        for p in S.ALPHA_POSITIONS
    ]
    beta_pos = [
        (f"position:{p.isin}" if p.isin else f"position:cash:{p.name}", p.value_chf) for p in S.BETA_POSITIONS
    ]
    t = S.ALPHA_TARIFF
    docs = [
        _doc(
            "alpha_costs_and_charges_2025-2026.pdf",
            "cost_report",
            [("meta:average_assets", S.ALPHA_TOTAL)]
            + [(f"fee:{code}", v) for _l, code, v in S.ALPHA_COST_REPORT]
            + [
                ("total:service", sum((v for *_x, v in S.ALPHA_COST_REPORT), Decimal(0))),
                ("reported:product_costs", S.ALPHA_REPORTED_PRODUCT_COSTS),
                ("reported:retrocessions", S.ALPHA_RETROCESSIONS),
            ],
        ),
        _doc(
            "alpha_estratto_conto_Q3_2026_scan.pdf",
            "cash_statement",
            [(f"debit:{d}:{code}", v) for d, _l, code, v in S.ALPHA_CASH_DEBITS],
        ),
        _doc(
            "alpha_price_schedule_2026.pdf",
            "tariff",
            [
                ("rule:ADVISORY_FEE:rate", t["advisory_pct"]),
                ("rule:CUSTODY_FEE:rate", t["custody_pct"]),
                ("rule:CUSTODY_FEE:minimum", t["custody_min"]),
                ("rule:BROKERAGE:rate", t["brokerage_pct"]),
                ("rule:BROKERAGE:minimum", t["brokerage_min"]),
                ("rule:TRANSFER_OUT:per_position", t["transfer_out_per_position"]),
            ],
        ),
        _doc(
            "alpha_statement_of_assets_2026-09-30.pdf",
            "portfolio_statement",
            _positions(alpha_pos, S.ALPHA_TOTAL),
        ),
        _doc(
            "beta_europe_price_schedule_2026.pdf",
            "tariff",
            [
                ("rule:CUSTODY_FEE:rate", S.BETA_LU_TARIFF["custody_pct"]),
                ("rule:CUSTODY_FEE:minimum", S.BETA_LU_TARIFF["custody_min_quarter"]),
            ],
        ),
        _doc(
            "beta_holdings_2026-09-30.xlsx",
            "portfolio_statement",
            [("fx:fx rate usd/chf", S.USD_CHF), *_positions(beta_pos, S.BETA_TOTAL)],
        ),
        *[_kid(f"kid_{isin}.pdf", k) for isin, k in S.KIDS.items()],
        _doc(
            "termsheet_ZZBRCSMI0010.pdf",
            "termsheet",
            # the issuer margin is not disclosed: it must stay unknown, never 0
            [("sp:distribution", S.STRUCTURED_TERMSHEET["distribution_fee_max"]), ("sp:entry_cost", None)],
        ),
    ]
    portfolio = GoldPortfolio(
        expect={
            "aum.total": "4300000.00",
            "current.billed_known": "40159.60",
            "current.embedded_known": "21290.00",
            "current.total_known": "61449.60",
            "current.is_complete": False,
            "scenarios.same_holdings.comparison.current_known": "60839.60",
            "scenarios.same_holdings.comparison.proposal_known": "54319.50",
            "scenarios.same_holdings.comparison.annual_saving": "6520.10",
            "scenarios.optimized.comparison.annual_saving": "14700.10",
        },
        requests=["cost_report:Bank Beta (Synthetic)", "kid:ZZEMMKTA0019", "sp:ZZBRCSMI0010"],
        failed_checks=["tariff:5"],  # the Luxembourg price schedule must be rejected for CH booking
    )
    return Corpus(
        name="synthetic-p1042", folder=folder, docs=docs, portfolio=portfolio, domicile=S.CLIENT_DOMICILE
    )


def synthetic_p2077(folder: Path) -> Corpus:
    delta_codes = ["MGMT_DISCRETIONARY", "CUSTODY_FEE", "BROKERAGE", "ACCOUNT_FEE"]
    ng_codes = ["BROKERAGE", "PLATFORM_FIXED", "FX_COMMISSION"]
    k = A.DELTA_KID
    docs = [
        _doc(
            "delta_rendiconto_costi_oneri_2025-2026.pdf",
            "cost_report",
            [(f"fee:{c}", v) for c, (_l, v) in zip(delta_codes, A.DELTA_COSTS, strict=True)]
            + [
                ("total:service", sum((v for _l, v in A.DELTA_COSTS), Decimal(0))),
                ("reported:product_costs", A.DELTA_PRODUCT_COSTS),
                ("reported:retrocessions", A.DELTA_INDUCEMENTS),
            ],
        ),
        _doc(
            "delta_situazione_patrimoniale_2026-09-30.pdf",
            "portfolio_statement",
            [
                ("fx:EURCHF", A.EUR_CHF),
                *_positions(
                    [(f"position:{isin}", v) for _n, isin, _q, _p, v in A.DELTA_POSITIONS]
                    + [("position:cash:Conto corrente EUR", A.DELTA_CASH)],
                    A.DELTA_TOTAL,
                ),
            ],
        ),
        _doc(
            "kid_ZZFBILIT0018_it.pdf",
            "kid",
            [
                ("kid:FUND_ENTRY_CHARGE", k["entry_max"]),
                ("kid:FUND_EXIT_CHARGE", Decimal("0.00")),
                ("kid:FUND_ONGOING", k["ongoing"]),
                ("kid:FUND_MGMT_FEE", k["mgmt"]),
                ("kid:FUND_TRANSACTION", k["transaction"]),
                ("kid:FUND_PERFORMANCE", Decimal("0.00")),
            ],
        ),
        _doc(
            "northgate_activity_statement_2025-2026.pdf",
            "portfolio_statement",
            [("fx:USDCHF", A.USD_CHF)]
            + _positions(
                [(f"position:{isin}", v) for _n, isin, _q, _p, v in A.NORTHGATE_POSITIONS]
                + [("position:cash:Cash USD", A.NORTHGATE_CASH)],
                A.NORTHGATE_TOTAL,
            )
            + [(f"fee:{c}", v) for c, (_l, v) in zip(ng_codes, A.NORTHGATE_FEES, strict=True)],
        ),
    ]
    portfolio = GoldPortfolio(
        expect={
            "aum.total": "1821750.00",  # 1,050,000 EUR x 0.9350 + 1,050,000 USD x 0.8000
            "scenarios.current_comparable.total_known": "25264.35",
            "scenarios.current_comparable.is_complete": False,
            "scenarios.same_holdings.comparison.annual_saving": "-2588.07",  # proposal is dearer: say so
        },
    )
    return Corpus(
        name="synthetic-p2077", folder=folder, docs=docs, portfolio=portfolio, domicile=A.CLIENT_DOMICILE
    )


def ocrbench(folder: Path = SPECIMEN_FILES, gt_path: Path = OCRBENCH_GT) -> Corpus:
    """Hand-checked fee figures per benchmark page. Simulated-scan variants share the original's labels,
    so only original pages are listed here; scans are produced by the corpus variant ``scan``."""
    gt = json.loads(gt_path.read_text(encoding="utf-8"))["pages"]
    pages_json = json.loads((gt_path.parent / "pages.json").read_text(encoding="utf-8"))
    meta = {p["id"]: p for p in (pages_json["pages"] if isinstance(pages_json, dict) else pages_json)}
    by_file: dict[str, GoldDoc] = {}
    for pid, page in gt.items():
        m = meta.get(pid)
        if not m or m.get("variant", "original") != "original":
            continue
        doc = by_file.setdefault(m["file"], GoldDoc(file=m["file"], pages=[], kinds=FEE_KINDS))
        doc.pages.append(m["page"])  # type: ignore[union-attr]
        doc.items += [
            GoldItem(file=m["file"], label=i["label"], value=i["value"], page=m["page"], bbox=i.get("bbox"))
            for i in page["items"]
        ]
    return Corpus(name="ocrbench", folder=folder, docs=list(by_file.values()))


def manifest(path: Path = SPECIMENS, folder: Path = SPECIMEN_FILES) -> Corpus:
    """Rows with an ``expected`` column ('doc_type=kid; kid:FUND_ONGOING=1.78'): partial labels, so recall
    only."""
    docs = []
    with path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            parts = [p.partition("=") for p in (row.get("expected") or "").split(";") if "=" in p]
            if not parts:
                continue
            kv = {k.strip(): v.strip() for k, _s, v in parts}
            doc_type = kv.pop("doc_type", None)
            items = [
                GoldItem(file=row["file"], key=k, value=v.split()[0])
                for k, v in kv.items()
                if not k.startswith("meta:")
            ]
            docs.append(GoldDoc(file=row["file"], doc_type=doc_type, items=items, exhaustive=False))
    return Corpus(name=path.stem, folder=folder, docs=docs)
