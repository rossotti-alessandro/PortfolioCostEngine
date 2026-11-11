"""Extraction strategies under test. A strategy is any ``(filename, bytes) -> Prediction`` function.

``baseline`` is the production pipeline (what the upload API runs). ``sabotaged`` is the baseline with
deliberately wrong numbers: the protocol's own sanity check (it must score lower, or the scorer is
blind). Any other strategy plugs in as ``package.module:function`` without touching this file.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable
from decimal import Decimal

from pydantic import BaseModel

from ..extraction.models import DocType
from ..extraction.parsers import extract


class Prediction(BaseModel):
    doc_type: str
    facts: list[dict]  # Fact.model_dump() shape: key, kind, label, value, fee_code, evidence{page,bbox,...}
    profile: dict = {}  # DocumentProfile.model_dump(): institution, dates, currency (the analysis needs them)
    needs_review: bool = False
    pages: int = 0


Strategy = Callable[[str, bytes], Prediction]


def baseline(filename: str, data: bytes) -> Prediction:
    res, _pages = extract(filename, data)
    prof = res.profile
    return Prediction(
        doc_type=prof.doc_type.value,
        facts=[f.model_dump(mode="json") for f in res.facts],
        needs_review=prof.doc_type == DocType.UNKNOWN or bool(prof.warnings),
        profile=prof.model_dump(),
        pages=prof.page_count,
    )


def sabotaged(filename: str, data: bytes) -> Prediction:
    """Every other value off by 10x, every unknown turned into 0: the two errors the product fears most."""
    p = baseline(filename, data)
    for i, f in enumerate(p.facts):
        if f.get("value") is None and f.get("kind") != "meta":
            f["value"] = "0"
        elif f.get("value") is not None and i % 2 == 0:
            f["value"] = str(Decimal(f["value"]) * 10)
    return p


BUILTIN: dict[str, Strategy] = {"baseline": baseline, "sabotaged": sabotaged}


def resolve(name: str) -> Strategy:
    if name in BUILTIN:
        return BUILTIN[name]
    module, _, func = name.partition(":")
    if not func:
        raise ValueError(
            f"unknown strategy {name!r}: use one of {sorted(BUILTIN)} or package.module:function"
        )
    return getattr(importlib.import_module(module), func)
