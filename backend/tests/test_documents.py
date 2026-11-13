"""Several documents read at once give the same result as one at a time (SC-5.20)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from pce.demo import generate
from pce.extraction import documents, parsers


def _facts(res) -> list:
    return [(f.key, f.kind, f.value, f.currency, f.evidence.page, f.evidence.bbox) for f in res.facts]


@pytest.fixture(scope="module")
def pack(tmp_path_factory: pytest.TempPathFactory) -> list[Path]:
    """The SYNTHETIC P-1042 documents, born-digital and the scanned statement."""
    return sorted(p for p in generate.generate(tmp_path_factory.mktemp("p1042")) if p.suffix == ".pdf")


def test_one_worker_runs_inline(monkeypatch: pytest.MonkeyPatch, pack: list[Path]) -> None:
    monkeypatch.setenv("PCE_DOC_WORKERS", "1")
    monkeypatch.setattr(documents, "_pool", lambda: pytest.fail("no process pool with one worker"))
    res, _ = documents.extract(pack[0].name, pack[0].read_bytes())
    assert res.facts


def test_parallel_documents_match_sequential(monkeypatch: pytest.MonkeyPatch, pack: list[Path]) -> None:
    sequential = [_facts(parsers.extract(p.name, p.read_bytes())[0]) for p in pack]
    monkeypatch.setenv("PCE_DOC_WORKERS", "2")
    monkeypatch.setattr(documents, "_POOL", None)
    with ThreadPoolExecutor(3) as requests:  # three uploads at once, as the Documents page sends them
        parallel = list(requests.map(lambda p: _facts(documents.extract(p.name, p.read_bytes())[0]), pack))
    documents._POOL.shutdown()  # type: ignore[union-attr]
    monkeypatch.setattr(documents, "_POOL", None)
    assert parallel == sequential
