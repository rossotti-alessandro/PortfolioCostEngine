"""Can an OCR verifier tell a misread fee figure from a correct one? (SC-5.13)

MiniCPM-OCR-Jev (openbmb, Apache-2.0, 2B) scores 0-1 whether an OCR result matches the region it was
read from. It looks at three things: the region crop, the OCR text, and that text rendered as an image.
This script measures it on our pages, against the OCR engines' own confidence as the baseline.

A sample is the line an OCR engine read around one gold fee figure: the engine's line whose box
holds the figure's centre. The line is "right" when it has exactly the numbers the PDF text layer
has inside the same box (a misread number, a dropped or invented digit makes it wrong; wording
differences do not). Scan copies reuse their original page's gold boxes and text layer (same
geometry, small skew), with a wider tolerance.

    build   samples + crops      -> var/ocrbench/jev/samples.json, crops/
    (node data/specimens/ocrbench/jev_render.mjs renders each candidate text -> renders/)
    score   Jev scores           -> var/ocrbench/jev/scores.json   (resumable)
    report  AUROC, catch rate at a review budget, vs the engines' own confidence -> printed + jev.json

Lab venv: var/ocrbench/.venv/bin/python data/specimens/ocrbench/jev_verify.py build|score|report
Rendering follows the vendor renderer's page CSS (18 px, line-height 2, 1 px table borders, DPR 1,
white border trimmed) but not its Chromium/fonts build, so scores may sit off the published scale.
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
PAGES = ROOT / "var" / "ocrbench" / "pages"
OUT = ROOT / "var" / "ocrbench" / "out"
J = ROOT / "var" / "ocrbench" / "jev"
ENGINES = ["tesseract", "rapidocr", "doctr", "easyocr"]
REPO = "openbmb/MiniCPM-OCR-Jev"
SUBSET = 1000  # random lines scored (seed 513); the base rate of misreads is kept

# The vendor's prompt, byte for byte (infer_vllm.py, md5 9aab68e8ba8ab4da17ba9752bddb199c).
IMG = "<|vision_start|><|image_pad|><|vision_end|>"
INSTRUCTION = (
    "第一张图是原图，第二张图是上述 OCR 文本渲染得到的图片。\n"
    "请判断该 OCR 文本及其对应渲染图是否与原图内容一致。\n"
    "这是一个二分类任务：一致标为 1，不一致标为 0。"
)
SUFFIX = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"
POOLED_TOKEN_ID = 271
MAX_ASPECT = 199.0


def prompt(text: str) -> str:
    return f"<|im_start|>user\n{IMG}\nOCR文本：\n{text}\n{IMG}\n{INSTRUCTION}{SUFFIX}"


def numbers(text: str) -> list[str]:
    return sorted(re.findall(r"\d[\d'’.,]*\d|\d", text.replace("’", "'")))


def layer_words(page_id: str) -> list[dict]:
    """The PDF text layer's words in image pixels: the reference for what each line says."""
    import pdfplumber

    with pdfplumber.open(PAGES / f"{page_id}.pdf") as doc:
        return [
            {"t": w["text"], "cx": w["x0"] + w["x1"], "cy": w["top"] + w["bottom"]}  # centre, points * 2 / 2
            for w in doc.pages[0].extract_words()
        ]


def build() -> None:
    pages = json.loads((HERE / "pages.json").read_text(encoding="utf-8"))
    gold = json.loads((HERE / "groundtruth.json").read_text(encoding="utf-8"))["pages"]
    (J / "crops").mkdir(parents=True, exist_ok=True)
    samples = []
    for p in pages:
        src = p["id"].removesuffix("-scan")
        items = [g for g in gold.get(src, {}).get("items", []) if g.get("bbox")]
        if not items:
            continue
        tol = 14 if p["variant"] == "scan-sim" else 6
        ref = layer_words(src)
        img = Image.open(PAGES / f"{p['id']}.png").convert("RGB")
        for eng in ENGINES:
            f = OUT / eng / f"{p['id']}.json"
            if not f.exists():
                continue
            lines = [w for w in json.loads(f.read_text(encoding="utf-8")).get("words", []) if w.get("b")]
            for gi, g in enumerate(items):
                cx, cy = (g["bbox"][0] + g["bbox"][2]), (g["bbox"][1] + g["bbox"][3])  # points * 2 / 2 -> px
                hits = [
                    w for w in lines
                    if w["b"][0] - tol <= cx <= w["b"][2] + tol and w["b"][1] - tol <= cy <= w["b"][3] + tol
                ]
                if not hits:
                    continue
                w = min(hits, key=lambda w: (w["b"][2] - w["b"][0]) * (w["b"][3] - w["b"][1]))
                x0, y0, x1, y1 = (int(v) for v in w["b"])
                t2 = tol - 4  # reference words: centre inside the line box
                truth = " ".join(
                    r["t"] for r in ref if x0 - t2 <= r["cx"] <= x1 + t2 and y0 - t2 <= r["cy"] <= y1 + t2
                )
                if not numbers(truth):
                    continue  # the box does not hold the figure in the text layer: a location miss, not a read
                crop = img.crop((max(0, x0 - 4), max(0, y0 - 4), x1 + 4, y1 + 4))
                sid = f"{p['id']}__{eng}__{gi}"
                crop.save(J / "crops" / f"{sid}.png")
                samples.append({
                    "id": sid, "page": p["id"], "variant": p["variant"], "engine": eng,
                    "gold": g["value"], "text": w["t"], "truth": truth, "conf": w.get("c"),
                    "right": numbers(w["t"]) == numbers(truth), "width": crop.size[0],
                })
    import random

    keep = set(random.Random(513).sample(range(len(samples)), min(SUBSET, len(samples))))
    samples = [s for i, s in enumerate(samples) if i in keep]  # Jev takes seconds per line on CPU
    (J / "samples.json").write_text(json.dumps(samples, ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(samples), "samples,", sum(not s["right"] for s in samples), "misread")


def _pad(img: Image.Image) -> Image.Image:
    """The vendor pads (never resizes) crops past 199:1, to keep glyph scale."""
    w, h = img.size
    if max(w, h) / max(1, min(w, h)) <= MAX_ASPECT:
        return img
    nw, nh = (w, max(h, int(w / MAX_ASPECT + 1))) if w >= h else (max(w, int(h / MAX_ASPECT + 1)), h)
    c = Image.new("RGB", (nw, nh), "white")
    c.paste(img, ((nw - w) // 2, (nh - h) // 2))
    return c


def score() -> None:
    import torch
    from transformers import AutoProcessor, Qwen3_5ForSequenceClassification

    torch.set_num_threads(4)
    samples = json.loads((J / "samples.json").read_text(encoding="utf-8"))
    done_f = J / "scores.json"
    done = json.loads(done_f.read_text(encoding="utf-8")) if done_f.exists() else {}
    proc = AutoProcessor.from_pretrained(REPO)
    t = time.time()
    model, info = Qwen3_5ForSequenceClassification.from_pretrained(
        REPO, dtype=torch.float32, num_labels=2, output_loading_info=True
    )
    if info.get("missing_keys") or info.get("unexpected_keys"):
        sys.exit(f"checkpoint did not load cleanly: {info}")  # a random head would score noise
    model.eval()
    print(f"load {time.time() - t:.0f}s", flush=True)
    for i, s in enumerate(samples):
        if s["id"] in done or not (J / "renders" / f"{s['id']}.png").exists():
            continue
        t = time.time()
        ims = [_pad(Image.open(J / d / f"{s['id']}.png").convert("RGB")) for d in ("crops", "renders")]
        inputs = proc(text=[prompt(s["text"])], images=ims, return_tensors="pt")
        if int(inputs["input_ids"][0, -1]) != POOLED_TOKEN_ID:
            sys.exit("prompt does not end on the pooled token; the head would read the wrong position")
        with torch.inference_mode():
            logits = model(**inputs).logits.float()
        done[s["id"]] = float(torch.softmax(logits, -1)[0, 1])
        if i % 10 == 0:
            done_f.write_text(json.dumps(done), encoding="utf-8")
            print(i, s["id"], round(done[s["id"]], 3), s["right"], f"{time.time() - t:.1f}s", flush=True)
    done_f.write_text(json.dumps(done), encoding="utf-8")


def auroc(pos: list[float], neg: list[float]) -> float | None:
    """P(score of a right read > score of a misread), ties count half."""
    if not pos or not neg:
        return None
    wins = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg)
    return wins / (len(pos) * len(neg))


def report() -> None:
    samples = json.loads((J / "samples.json").read_text(encoding="utf-8"))
    sc = json.loads((J / "scores.json").read_text(encoding="utf-8"))
    rows = [s | {"jev": sc[s["id"]]} for s in samples if s["id"] in sc]
    out: dict = {"n": len(rows), "misread": sum(not r["right"] for r in rows), "by": {}}

    def stats(rs: list[dict], key: str) -> dict:
        rs = [r for r in rs if r.get(key) is not None]
        pos = [r[key] for r in rs if r["right"]]
        neg = [r[key] for r in rs if not r["right"]]
        res = {"n": len(rs), "misread": len(neg), "auroc": auroc(pos, neg)}
        for budget in (0.1, 0.2):  # send the lowest-scored share to review: how many misreads does it catch?
            k = round(len(rs) * budget)
            low = sorted(rs, key=lambda r: r[key])[:k]
            res[f"caught@{int(budget * 100)}%"] = (sum(not r["right"] for r in low) / len(neg)) if neg else None
        return res

    for name, rs in {"all": rows, "scans": [r for r in rows if r["variant"] == "scan-sim"],
                     **{e: [r for r in rows if r["engine"] == e] for e in ENGINES}}.items():
        out["by"][name] = {"jev": stats(rs, "jev"), "engine_conf": stats(rs, "conf")}
    (J / "jev.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    {"build": build, "score": score, "report": report}[sys.argv[1]]()
