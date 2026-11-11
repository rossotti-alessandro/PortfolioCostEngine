"""Second synthetic prospect (P-2077: Italian bank in EUR, US broker in USD) and real public documents.

P-2077 checks FX conversion at the rates printed on the client's own documents and the honest case where
the proposal is not cheaper. The public PDFs are third-party copyright, so they are not in git: run
``python -m pce.demo.public_corpus`` to fetch them; each test skips when its file is absent.
"""

from decimal import Decimal as Dec
from pathlib import Path

import pytest

from pce.demo import public_corpus
from pce.demo.archetypes import generate
from pce.demo.offline import load_folder, run
from pce.extraction.parsers import extract


@pytest.fixture(scope="module")
def p2077(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("p2077")
    generate(out)
    return out


def test_p2077_documents_classified(p2077):
    docs, _ = load_folder(p2077)
    assert "unknown" not in {d["doc_type"] for d in docs}


def test_p2077_converts_at_printed_rates_and_reports_no_saving(p2077):
    a = run(p2077)
    assert Dec(a["aum"]["total"]) == Dec("1821750.00")  # 1,050,000 EUR x 0.9350 + 1,050,000 USD x 0.8000
    cur = a["scenarios"]["current_comparable"]
    assert Dec(cur["total_known"]) == Dec("25264.35")
    assert cur["is_complete"] is False  # broker custody and the iShares KID are missing, not zero
    cmp = a["scenarios"]["same_holdings"]["comparison"]
    assert Dec(cmp["annual_saving"]) == Dec("-2588.07")  # proposal costs more on known costs
    assert all(c["status"] == "pass" for c in a["checks"] if c["key"].startswith("reconcile:"))
    assert any("printed rate" in c["title"] for c in a["checks"])


def _public(name: str) -> tuple[dict, dict]:
    entry = next(e for e in public_corpus.entries() if e["file"] == name)
    path = public_corpus.TARGET / name
    if not path.exists():
        pytest.skip(f"{name} not fetched (python -m pce.demo.public_corpus)")
    res, _ = extract(name, path.read_bytes())
    return res.model_dump(mode="json"), public_corpus.expected(entry)


@pytest.mark.parametrize("name", [e["file"] for e in public_corpus.entries()])
def test_public_document_matches_manifest(name):
    res, exp = _public(name)
    assert res["profile"]["doc_type"] == exp.pop("doc_type")
    facts = {f["key"]: f for f in res["facts"]}
    for key, want in exp.items():
        if key.startswith("meta:issuing_entity.jurisdiction"):
            assert facts["meta:issuing_entity"]["extra"]["jurisdiction"] == want
            continue
        got = facts[key]
        assert Dec(str(got["value"])) == Dec(want.split()[0]), key
        assert got["evidence"]["page"] >= 1 and got["evidence"]["bbox"], key  # every value has a source box


def _pdf(tmp_path: Path, name: str, title: str, rows: list[tuple[str, str]]) -> tuple[dict, list]:
    from pce.demo.generate import Doc

    d = Doc(tmp_path / name, title)
    d.header("Synthetic Fund Management Ltd", "Dublin, Ireland", title, "ISIN IE00B4L5Y983")
    for label, value in rows:
        d.row([(50, label, "l"), (400, value, "l")])
    d.save()
    res, _ = extract(name, (tmp_path / name).read_bytes())
    return res.model_dump(mode="json"), res.facts


def test_kid_with_wrapped_cost_label_and_curly_apostrophe(tmp_path):
    # Real KIDs wrap "Frais de gestion et autres frais administratifs..." over two lines (corpus finding).
    res, facts = _pdf(
        tmp_path,
        "kid_fr.pdf",
        "Document d’informations clés",
        [("Frais de gestion et", "0,20 % de la valeur de votre investissement par an"), ("autres frais", "")],
    )
    assert res["profile"]["doc_type"] == "kid"
    assert {f.key: f.value for f in facts}.get("kid:FUND_ONGOING") == "0.20"


def test_fund_factsheet_is_not_a_statement_or_kid(tmp_path):
    res, _ = _pdf(
        tmp_path,
        "factsheet.pdf",
        "Monthly factsheet · Key information document available",
        [("Positions", "Market value"), ("Ongoing charges", "0.20%")],
    )
    assert res["profile"]["doc_type"] == "unknown"


def test_kid_value_on_the_line_below_its_label(tmp_path):
    from pce.demo.generate import Doc

    d = Doc(tmp_path / "kid_it.pdf", "Documento contenente le informazioni chiave")
    d.header(
        "Synthetic SGR S.p.A.", "Milano", "Documento contenente le informazioni chiave", "ISIN IE00B4L5Y983"
    )
    d.row([(50, "Commissioni di gestione e", "l")])
    d.row([(50, "altri costi amministrativi", "l"), (400, "1,20 % del valore", "l")])
    d.row([(50, "Totale", "l"), (400, "250,000", "l")])  # an ambiguous amount must not fail the document
    d.save()
    res, _ = extract("kid_it.pdf", (tmp_path / "kid_it.pdf").read_bytes())
    assert {f.key: f.value for f in res.facts}.get("kid:FUND_ONGOING") == "1.20"


def test_statement_without_isins_reconciles_holdings_to_account_totals(tmp_path):
    # UK platform statements (corpus: Fidelity QPR) list "Quantity | Price | Value" in GBP, no ISIN column,
    # wrap long fund names, put cash on the next line, and end with an allocation table of weights.
    from pce.demo.generate import Doc

    d = Doc(tmp_path / "uk.pdf", "Portfolio report")
    d.header("Synthetic Platform Ltd", "London", "SYNTHETIC Portfolio report", "Valuation of each investment")
    d.row([(50, "Investment", "l"), (300, "Quantity", "r"), (400, "Price", "r"), (500, "Value", "r")])
    d.row(
        [
            (50, "Alpha Global Equity W Acc", "l"),
            (300, "1,000.00", "r"),
            (400, "£2.50", "r"),
            (500, "£2,500.00", "r"),
        ]
    )
    d.row([(50, "Beta Very Long Fund Name Accumulation", "l")])
    d.row([(300, "200.00", "r"), (400, "£10.00", "r"), (500, "£2,000.00", "r")])
    d.row([(50, "Money held as cash", "l"), (500, "£500.00", "r")])
    d.row([(50, "Total account value", "l"), (500, "£5,000.00", "r")])
    d.row([(50, "Name", "l"), (300, "Charge", "r"), (400, "Rating", "r"), (500, "Weight", "r")])
    d.row([(50, "4 Gamma Income I Acc", "l"), (300, "0.80", "r"), (400, "5.93", "r"), (500, "4.75", "r")])
    d.save()
    res, _ = extract("uk.pdf", (tmp_path / "uk.pdf").read_bytes())
    pos = {f.label: (f.value, f.currency) for f in res.facts if f.kind == "position"}
    assert res.profile.doc_type == "portfolio_statement"
    assert sum(Dec(v) for v, _ in pos.values()) == Dec("5000.00")  # the weight row is not a holding
    assert pos["Beta Very Long Fund Name Accumulation"] == ("2000.00", "GBP")
    assert all(f.evidence.bbox for f in res.facts if f.kind == "position")


def test_holdings_table_with_cost_columns_and_symbol_in_header(tmp_path):
    # AJ Bell-style layout (corpus): "Price (£) | Value (£) | Cost (£) | Change (%)", a wide total row,
    # then a capital-gains disposal table with an ISIN that is not a holding.
    from pce.demo.generate import Doc

    d = Doc(tmp_path / "uk2.pdf", "Client valuation")
    d.header("Synthetic Platform Ltd", "London", "SYNTHETIC client report", "Valuation breakdown")
    cols = [(50, "l"), (250, "r"), (310, "r"), (370, "r"), (430, "r"), (490, "r")]

    def row(*cells: str) -> None:
        d.row([(x, t, a) for (x, a), t in zip(cols, cells, strict=False)])

    row("Holding name", "Quantity", "Price (£)", "Value (£)", "Cost (£)", "Change (%)")
    row("ALPHA EQUITY I ACC", "1,000.00000", "2.50000", "2,500.00", "2,000.00", "25.00")
    row("BETA BOND FUND INC", "400.00000", "5.00000", "2,000.00", "2,100.00", "-4.76")
    row("Total", "4,500.00", "4,100.00", "9.76")
    row("Date", "ISIN", "Holding name", "Quantity", "Proceeds (£)", "Profit/loss (£)")
    row("16/04/2019", "IE00B3NS4D25", "Sold Fund", "100.00", "£1,000.00", "£200.00")
    d.save()
    res, _ = extract("uk2.pdf", (tmp_path / "uk2.pdf").read_bytes())
    pos = {f.label: (f.value, f.currency) for f in res.facts if f.kind == "position"}
    assert res.profile.doc_type == "portfolio_statement"
    assert pos == {"ALPHA EQUITY I ACC": ("2500.00", "GBP"), "BETA BOND FUND INC": ("2000.00", "GBP")}
    assert {f.key: f.value for f in res.facts}["total:assets"] == "4500.00"


def test_possible_misses_flag_unread_cost_lines_only():
    from pce.extraction.layout import Cell, Line, PageInfo
    from pce.extraction.models import Evidence, Fact
    from pce.extraction.parsers import _possible_misses

    def line(y: float, *cells: str) -> Line:
        return Line(
            page=1,
            cells=[Cell(c, (50.0 + 200 * i, y, 150.0 + 200 * i, y + 10)) for i, c in enumerate(cells)],
            engine="t",
        )

    page = PageInfo(
        1,
        595,
        842,
        "t",
        [
            line(100, "Custody fee", "0.15%"),  # read below: covered
            line(130, "Brokerage commission", "CHF 1,250.00"),  # not read: a possible miss
            line(160, "Custody account maintenance", "06"),  # table of contents page number: ignored
        ],
    )
    read = Fact(
        key="fee:CUSTODY_FEE",
        kind="fee_rule",
        field="rate",
        label="Custody fee",
        value="0.15",
        evidence=Evidence(page=1, bbox=[250, 100, 350, 110]),
    )
    misses = _possible_misses([page], [read])
    assert [m["text"] for m in misses] == ["Brokerage commission CHF 1,250.00"]
