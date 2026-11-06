"""Run extraction + analysis on a folder of documents without the API/DB (used by tests and CLI)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from ..analysis import analyse
from ..extraction.parsers import extract
from . import spec


def load_folder(folder: Path) -> tuple[list[dict], list[dict]]:
    documents, facts = [], []
    fid = 1
    for i, f in enumerate(sorted(p for p in folder.iterdir() if p.is_file()), start=1):
        res, _pages = extract(f.name, f.read_bytes())
        documents.append({"id": i, "filename": f.name, "doc_type": res.profile.doc_type.value,
                          "profile": res.profile.model_dump()})
        for fact in res.facts:
            d = fact.model_dump()
            d.update(id=fid, document_id=i, status="extracted")
            facts.append(d)
            fid += 1
    return documents, facts


def run(folder: Path) -> dict:
    docs, facts = load_folder(folder)
    return analyse({"domicile": spec.CLIENT_DOMICILE}, docs, facts, spec.PROPOSAL_DEFAULTS)


if __name__ == "__main__":
    print(json.dumps(run(Path(sys.argv[1])), indent=1))
