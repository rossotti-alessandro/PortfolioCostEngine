"""Agentic revalidation in the workflow arena (SC-5.14): the backend graph with the lab's specialists.

The graph is ``pce.extraction.revalidate`` (the same code the app would run). This file plugs in the
specialists that need the model lab, so their effect can be measured before any of them enters the app:

    readers    RapidOCR and docTR (stored lab outputs, read the rendered page, a different engine family
               from both the text layer and Tesseract), then the vision reader's table row (PaddleOCR-VL,
               stored, 23 pages): the same value in a table row that shares a word with the label.
    checks     the backend's arithmetic: rows that add up to the printed total, KID amount vs %.
    critic     the local language model of ``agent.py`` (Qwen3-4B-Instruct-2507). Its decisions are
               replayed from the agent run's log (same model, same candidates, same order), and only
               "not a fee" / "unsure" count, as flags.

Every variant starts from the facts of finder + verify (the production path of PR #15), recomputed here
so the graph sees real ``Fact`` objects, and writes ``var/arena/revalidate/<variant>.json`` (predictions)
and ``seconds.json`` for ``run.py``.

Backend env of a checkout with the finder:
    cd backend && uv run python ../data/specimens/arena/revalidate_lab.py
"""

from __future__ import annotations

import json
import re
import sys
import time
from collections.abc import Callable
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "data" / "specimens" / "strategies"))
import strategies as S  # noqa: E402  (finder + verify harness, PR #15)

from pce.extraction import finder, verify  # noqa: E402
from pce.extraction.models import Fact  # noqa: E402
from pce.extraction.revalidate import (  # noqa: E402
    BACKEND_CHECKS,
    Opinion,
    PageSpecialist,
    Reader,
    Specialists,
    Verdict,
    revalidate,
)

BENCH = ROOT / "data" / "specimens" / "ocrbench"
OUT = ROOT / "var" / "arena" / "revalidate"
AGENT = ROOT / "var" / "arena" / "agent" / "Qwen3-4B-Instruct-2507"


def stored_reader(engine: str, page: dict, used: set[str]) -> Reader:
    """An engine's stored reading of the whole page, asked whether it saw the value at the value's box."""

    def read(f: Fact) -> Opinion:
        got = S.stored_pages(engine, page)
        if got is None:
            return Opinion(engine, Verdict.ABSTAIN, "no reading of this page")
        used.add(engine)
        c = verify._second_reading(f, got[0])  # same matching rule as verify
        return Opinion(engine, Verdict.CONFIRM if c.passed else Verdict.ABSTAIN, c.detail)

    return read


def _digits(s: str) -> str:
    return re.sub(r"\D", "", s).lstrip("0")


def vision_row_reader(page: dict, used: set[str]) -> Reader:
    """PaddleOCR-VL's table rows: the same digits in a row that shares a word with the fact's label."""

    def read(f: Fact) -> Opinion:
        d = S.stored("paddleocr_vl", page["id"])
        if not d:
            return Opinion("vision_row", Verdict.ABSTAIN, "vision reader did not run on this page")
        used.add("paddleocr_vl")
        want = _digits(str(f.extra.get("printed") or f.value))
        words = {w for w in re.findall(r"[a-zà-ÿ]{4,}", f.label.lower())}
        for t in d.get("tables") or []:
            for r in t.get("rows") or []:
                text = " ".join(r).lower()
                if (
                    want
                    and any(_digits(c) == want for c in r)
                    and words & set(re.findall(r"[a-zà-ÿ]{4,}", text))
                ):
                    return Opinion("vision_row", Verdict.CONFIRM, " | ".join(r)[:120])
        return Opinion("vision_row", Verdict.ABSTAIN, "value not in a matching table row")

    return read


def replayed_critic(pid: str, zeros_trusted: bool) -> PageSpecialist | None:
    """The agent's decisions for this page: "c<n>" is the n-th candidate, the same order as these facts."""
    f = AGENT / f"{pid}.json"
    if not f.exists():
        return None
    log = json.loads(f.read_text(encoding="utf-8"))["log"]
    decisions = {k: v for step in log for k, v in step.get("decisions", {}).items()}

    def critic(facts: list[Fact]) -> dict[int, Opinion]:
        out = {}
        for i, fact in enumerate(facts):
            d = decisions.get(f"c{i + 1}")
            if d not in ("not_fee", "unsure"):
                continue
            if zeros_trusted and fact.value not in (None, "") and float(fact.value) == 0:
                continue  # the arena showed the model mistakes "0 USD entry costs" for "no fee"
            out[i] = Opinion("critic", Verdict.FLAG, f"model: {d}")
        return out

    return critic


def critic_seconds(pid: str) -> float:
    f = AGENT / f"{pid}.json"
    return json.loads(f.read_text(encoding="utf-8"))["seconds"] if f.exists() else 0.0


Builder = Callable[[dict, set[str]], Specialists | None]
VARIANTS: dict[str, Builder] = {
    "arithmetic": lambda p, u: Specialists(checks=BACKEND_CHECKS),  # what the app runs (PCE_REVALIDATE=1)
    "readers": lambda p, u: Specialists(
        readers=[stored_reader("rapidocr", p, u), stored_reader("doctr", p, u), vision_row_reader(p, u)]
    ),
    "readers_arithmetic": lambda p, u: Specialists(
        readers=[stored_reader("rapidocr", p, u), stored_reader("doctr", p, u), vision_row_reader(p, u)],
        checks=BACKEND_CHECKS,
    ),
    "full": lambda p, u: (
        Specialists(
            readers=[stored_reader("rapidocr", p, u), stored_reader("doctr", p, u), vision_row_reader(p, u)],
            checks=BACKEND_CHECKS,
            critic=c,
        )
        if (c := replayed_critic(p["id"], zeros_trusted=False))
        else None
    ),
    "full_zeros": lambda p, u: (
        Specialists(
            readers=[stored_reader("rapidocr", p, u), stored_reader("doctr", p, u), vision_row_reader(p, u)],
            checks=BACKEND_CHECKS,
            critic=c,
        )
        if (c := replayed_critic(p["id"], zeros_trusted=True))
        else None
    ),
}


def finder_verify(p: dict) -> tuple[list[Fact], float]:
    """The production path of PR #15 (``strategies.verified_crops``), returning the facts themselves."""
    pages, secs = S.text_pages(p["id"])
    facts = finder.find_fees(pages)
    t0 = time.perf_counter()
    verify.verify(facts, pages, verify.second_reading((S.PAGES / f"{p['id']}.pdf").read_bytes(), facts))
    return facts, secs + time.perf_counter() - t0


def main() -> None:
    pages = json.loads((BENCH / "pages.json").read_text(encoding="utf-8"))
    gold = json.loads((BENCH / "groundtruth.json").read_text(encoding="utf-8"))["pages"]
    base = json.loads(
        (ROOT / "var" / "strategies" / "finder @text + verify(tesseract crops).json").read_text(
            encoding="utf-8"
        )
    )
    OUT.mkdir(parents=True, exist_ok=True)
    dumps: dict[str, dict[str, list[dict]]] = {k: {} for k in VARIANTS}
    secs: dict[str, dict[str, float]] = {k: {} for k in VARIANTS}
    paths: dict[str, dict[str, int]] = {k: {} for k in VARIANTS}
    for p in pages:
        if (p.get("gt_from") or p["id"]) not in gold:
            continue
        facts, base_s = finder_verify(p)
        # same candidates, same order as the dump the agent reviewed: the critic replay depends on it
        assert [f.value for f in facts] == [d["value"] for d in base[p["id"]]], p["id"]
        for name, build in VARIANTS.items():
            used: set[str] = set()
            sp = build(p, used)
            if sp is None:
                continue
            copies = [f.model_copy(deep=True) for f in facts]
            t0 = time.perf_counter()
            out = revalidate(copies, sp)
            graph_s = time.perf_counter() - t0
            assert [(f.value, f.label, f.evidence.bbox) for f in out] == [
                (f.value, f.label, f.evidence.bbox) for f in facts
            ]  # the graph changes reviews only
            # stored readers were not re-run: their stored time counts when the graph asked them
            extra = sum((S.stored(e, p["id"]) or {}).get("seconds", 0.0) for e in used)
            extra += critic_seconds(p["id"]) if sp.critic else 0.0
            dumps[name][p["id"]] = [S._pred(f) for f in out]
            secs[name][p["id"]] = round(base_s + graph_s + extra, 2)
            for f in out:
                key = "→".join(f.extra["revalidation_path"])
                paths[name][key] = paths[name].get(key, 0) + 1
    for name, d in dumps.items():
        (OUT / f"{name}.json").write_text(json.dumps(d, ensure_ascii=False, default=str), encoding="utf-8")
    (OUT / "seconds.json").write_text(json.dumps(secs), encoding="utf-8")
    (OUT / "paths.json").write_text(json.dumps(paths, ensure_ascii=False, indent=1), encoding="utf-8")
    for name in VARIANTS:
        print(name, len(dumps[name]), "pages", paths[name])


if __name__ == "__main__":
    main()
