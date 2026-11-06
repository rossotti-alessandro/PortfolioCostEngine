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
