"""Agentic workflow for the workflow arena (SC-5.10): a local language model reviews fee candidates.

The deterministic finder + verify workflow proposes candidates (label, value, page box). A small local
language model (Qwen3-1.7B, Apache-2.0, CPU) then acts as the reviewer an analyst would be:

1. It sees the page heading and the candidates, each with the table row and header around it as a
   vision model (PaddleOCR-VL) read it, and may call the ``reread`` tool: another OCR engine's
   reading (RapidOCR) of the box where a value was found.
2. With the tool results it decides, per candidate id: ``fee``, ``not_fee`` or ``unsure``.

The model never writes a number. It can only answer with candidate ids and one of three words;
``apply_decisions`` builds the output from the candidates themselves, so every value keeps the box the
finder read it from. An id the model skipped, or an answer it garbled, leaves the candidate as it was
(a doubt never removes a figure silently). ``unsure`` sends the figure to analyst review.

Local only: no client data, no network at run time (weights from the Hugging Face cache).

Runs in the benchmark venv (torch + transformers), reading the candidates the harness dumped:
    var/ocrbench/.venv/bin/python data/specimens/arena/agent.py [--model Qwen/Qwen3-1.7B] [--dtype float32] [--only <page id>]
Writes var/arena/agent/<model>/<page id>.json: {"preds": [...], "seconds": s, "log": [...]}.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CANDS = ROOT / "var" / "arena" / "wt" / "var" / "strategies" / "finder @text + verify(tesseract crops).json"
STORED = ROOT / "var" / "ocrbench" / "out"
OUT = ROOT / "var" / "arena" / "agent"
CHUNK = 20  # candidates per model call: keeps the prompt short enough for a 1.7B model on CPU
DECISIONS = ("fee", "not_fee", "unsure")

SYSTEM = (
    "You review figures found on one page of a bank or fund document (price list, KID, cost report, statement). "
    "A figure is a FEE when it is a cost, charge, commission, tax or cost ratio the client pays or bears "
    "(also 0% or a minimum or maximum charge). It is NOT a fee when it is a price, a quantity, a position value, "
    "a return or performance, a date, a page number or a threshold that is not itself charged. In cost examples "
    "the invested amount (e.g. 10 000) is not a fee, but the costs shown for it (total costs, cost impact per "
    "year, entry or exit costs) are fees. Most candidates are fees: answer not_fee only when the label, context or table "
    "row clearly shows one of those non-fee things. You never write numbers: you only answer with candidate ids."
)
ASK_TOOLS = (
    "Tools you may call before deciding:\n"
    '  reread: a second OCR engine reads the value box again (use when the value looks misread)\n'
    'Answer ONLY with JSON: {"reread": [ids]}. Use [] when you need nothing.'
)
ASK_DECIDE = (
    'Decide each candidate. Answer ONLY with JSON mapping every id to "fee", "not_fee" or "unsure", '
    'e.g. {"c1": "fee", "c2": "not_fee"}. Use "unsure" when the page does not make it clear.'
)


# ---------- tools (deterministic, over stored outputs of the model lab) ----------


def _stored(engine: str, pid: str) -> dict | None:
    f = STORED / engine / f"{pid}.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


def reread(pid: str, cand: dict) -> str:
    """RapidOCR's words inside the candidate box (lab boxes are pixels at 144 dpi = PDF points x 2)."""
    o, b = _stored("rapidocr", pid), cand.get("bbox")
    if not o or not b:
        return "no second reading"
    x0, y0, x1, y1 = (v * 2 for v in b)
    words = [w["t"] for w in o.get("words", []) if w.get("b") and
             w["b"][0] < x1 + 4 and w["b"][2] > x0 - 4 and w["b"][1] < y1 + 4 and w["b"][3] > y0 - 4]  # fmt: skip
    return " ".join(words)[:80] or "nothing read there"


def table_row(pid: str, cand: dict) -> str:
    """The vision model's table row holding this value, with that table's first row as the header."""
    o = _stored("paddleocr_vl", pid)
    if not o:
        return "no table reading for this page"
    digits = lambda s: re.sub(r"\D", "", str(s))  # "1 767 CHF" and Decimal "1767" both give "1767"  # noqa: E731
    needle = digits(cand.get("value") or "").lstrip("0")
    for t in o.get("tables", []):
        rows = t.get("rows") or []
        for r in rows[1:]:
            if needle and any(digits(c).lstrip("0") == needle for c in r):
                return f"header: {' | '.join(rows[0])[:120]} ; row: {' | '.join(r)[:160]}"
    return "value not found in a table"


TOOLS = {"reread": reread}


# ---------- the guard: decisions only select and flag, never change a value ----------


def apply_decisions(cands: list[dict], decisions: dict[str, str]) -> list[dict]:
    """Keep ``fee``, flag ``unsure`` for review, drop ``not_fee``. Values, labels and boxes are copied from
    the candidates, never from the model; unknown ids and unknown words are ignored."""
    out = []
    for i, c in enumerate(cands):
        d = decisions.get(f"c{i + 1}")
        if d == "not_fee":
            continue
        p = dict(c)
        if d == "unsure":
            p["needs_review"] = True
            p["reasons"] = [*p.get("reasons", []), "agent_unsure"]
        out.append(p)
    return out


def parse_json(text: str) -> dict:
    """The first JSON object in the model's answer; {} when there is none (the guard then keeps everything)."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    m = re.search(r"\{.*\}", text, flags=re.S)
    if not m:
        return {}
    try:
        v = json.loads(m.group())
    except json.JSONDecodeError:
        return {}
    return v if isinstance(v, dict) else {}


# ---------- the model ----------


class Agent:
    def __init__(self, repo: str, dtype: str) -> None:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        torch.set_num_threads(4)
        self.tok = AutoTokenizer.from_pretrained(repo)
        self.model = AutoModelForCausalLM.from_pretrained(repo, dtype=getattr(torch, dtype))
        self.model.eval()
        self.torch = torch

    def ask(self, messages: list[dict], max_new: int) -> str:
        prompt = self.tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True,
                                              enable_thinking=False)  # fmt: skip
        ids = self.tok(prompt, return_tensors="pt")
        with self.torch.no_grad():
            out = self.model.generate(**ids, max_new_tokens=max_new, do_sample=False)
        return self.tok.decode(out[0][ids["input_ids"].shape[1] :], skip_special_tokens=True)


def describe(i: int, c: dict, row: str) -> str:
    flags = ", ".join(c.get("reasons") or []) or "none"
    return (f"c{i}: label={c.get('label', '')[:70]!r} value={c.get('value')} context={c.get('snippet', '')[:90]!r} "
            f"table={row!r} flags={flags}")  # fmt: skip


def review_page(agent: Agent, pid: str, heading: str, cands: list[dict]) -> tuple[list[dict], list[dict]]:
    decisions: dict[str, str] = {}
    log: list[dict] = []
    for start in range(0, len(cands), CHUNK):
        part = cands[start : start + CHUNK]
        # the table row is cheap and always useful, so it is looked up for every candidate up front;
        # the slower re-read is a tool the model asks for
        lines = "\n".join(describe(start + j + 1, c, table_row(pid, c)) for j, c in enumerate(part))
        base = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": f"Page: {heading}\nCandidates:\n{lines}\n\n{ASK_TOOLS}"}]  # fmt: skip
        calls = parse_json(agent.ask(base, 80))
        results = []
        for tool, fn in TOOLS.items():
            for cid in (calls.get(tool) or [])[:8] if isinstance(calls.get(tool), list) else []:
                m = re.fullmatch(r"c(\d+)", str(cid))
                if m and start < int(m.group(1)) <= start + len(part):
                    results.append(f"{tool}({cid}) -> {fn(pid, cands[int(m.group(1)) - 1])}")
        log.append({"tools": results})
        msgs = [*base, {"role": "assistant", "content": json.dumps(calls)},
                {"role": "user", "content": ("Tool results:\n" + "\n".join(results) + "\n\n" if results else "") + ASK_DECIDE}]  # fmt: skip
        got = parse_json(agent.ask(msgs, 12 * len(part) + 20))
        for k, v in got.items():
            if isinstance(v, str) and v in DECISIONS:
                decisions[k] = v
        log[-1]["decisions"] = {k: v for k, v in got.items() if isinstance(v, str)}
    return apply_decisions(cands, decisions), log


def heading(pid: str) -> str:
    o = _stored("pdfplumber", pid) or _stored("rapidocr", pid) or {}
    lines = [ln.strip() for ln in (o.get("text") or "").splitlines() if len(ln.strip()) > 3]
    return " / ".join(lines[:3])[:200]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen/Qwen3-1.7B")
    ap.add_argument("--only", default="")
    ap.add_argument("--dtype", default="float32", help="bfloat16 halves RAM for 4B models; float32 is faster on CPU")
    args = ap.parse_args()
    cands = json.loads(CANDS.read_text(encoding="utf-8"))
    out_dir = OUT / args.model.split("/")[-1]
    out_dir.mkdir(parents=True, exist_ok=True)
    agent = Agent(args.model, args.dtype)
    for pid, preds in cands.items():
        if args.only and pid not in args.only.split(","):
            continue
        dest = out_dir / f"{pid}.json"
        if dest.exists() and not args.only:
            continue
        t0 = time.perf_counter()
        out, log = review_page(agent, pid, heading(pid), preds) if preds else ([], [])
        secs = round(time.perf_counter() - t0, 1)
        dest.write_text(json.dumps({"preds": out, "seconds": secs, "log": log, "model": args.model},
                                   ensure_ascii=False, default=str, indent=1), encoding="utf-8")  # fmt: skip
        print(f"agent {pid} {len(preds)}->{len(out)} {secs}s", flush=True)


if __name__ == "__main__":
    main()
