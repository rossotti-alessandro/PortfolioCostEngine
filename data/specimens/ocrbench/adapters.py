"""Model adapters for the local OCR / layout / table / VLM benchmark (SC-5.6).

Every adapter takes a rendered page (PIL image at ``SCALE`` x 72 dpi) plus the
page's born-digital words when a pipeline needs them, and returns one dict:

    text     plain text or markdown the model read (may be "")
    words    [{"t": str, "b": [x0, y0, x1, y1], "c": conf}]  OCR lines or words
    regions  [{"label": str, "b": [...], "s": score}]         layout / ROI boxes
    tables   [{"b": [...] | None, "rows": [[cell, ...], ...]}]
    fees     [{"label": str, "value": str, "b": [...] | None}] direct fee answers

All boxes are in pixels of the rendered image, origin top-left. A model that
gives no box gets ``None``; boxes are never invented.

Models run on CPU only; nothing leaves the machine. Weights come from the
Hugging Face cache (``HF_HOME``), downloaded once.
"""

from __future__ import annotations

import html
import json
import re
from typing import Any, Callable

from PIL import Image

SCALE = 2  # render scale: 144 dpi; boxes / SCALE = PDF points
OCR_LANGS = "eng+deu+fra+ita"

Result = dict[str, Any]


def empty() -> Result:
    return {"text": "", "words": [], "regions": [], "tables": [], "fees": []}


def _torch():
    import torch

    torch.set_num_threads(4)
    return torch


# ---------------------------------------------------------------- HTML / markdown tables


def parse_tables(text: str) -> list[dict]:
    """Pull tables out of HTML (<table>), markdown pipes or OTSL text. Cells are plain text."""
    tables: list[dict] = []
    for m in re.finditer(r"<table.*?</table>", text, flags=re.S | re.I):
        rows = []
        for tr in re.findall(r"<tr.*?>(.*?)</tr>", m.group(0), flags=re.S | re.I):
            cells = re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", tr, flags=re.S | re.I)
            rows.append([html.unescape(re.sub(r"<[^>]+>", " ", c)).strip() for c in cells])
        if rows:
            tables.append({"b": None, "rows": rows})
    block: list[list[str]] = []
    for line in text.splitlines() + [""]:
        s = line.strip()
        if s.startswith("|") and s.count("|") >= 2:
            if re.fullmatch(r"\|?[\s:\-|]+\|?", s):
                continue
            block.append([c.strip() for c in s.strip("|").split("|")])
        elif block:
            tables.append({"b": None, "rows": block})
            block = []
    return tables


def strip_markup(text: str) -> str:
    t = re.sub(r"</t[dh]>", " | ", text, flags=re.I)
    t = re.sub(r"</tr>", "\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    return html.unescape(t)


# ---------------------------------------------------------------- classic OCR


def run_tesseract(img: Image.Image, **_: Any) -> Result:
    import pytesseract

    d = pytesseract.image_to_data(img, lang=OCR_LANGS, output_type=pytesseract.Output.DICT, timeout=180)
    out = empty()
    lines: dict[tuple, list[int]] = {}
    for i, t in enumerate(d["text"]):
        if not t.strip():
            continue
        lines.setdefault((d["block_num"][i], d["par_num"][i], d["line_num"][i]), []).append(i)
    for idx in lines.values():
        x0 = min(d["left"][i] for i in idx)
        y0 = min(d["top"][i] for i in idx)
        x1 = max(d["left"][i] + d["width"][i] for i in idx)
        y1 = max(d["top"][i] + d["height"][i] for i in idx)
        txt = " ".join(d["text"][i] for i in idx)
        conf = sum(float(d["conf"][i]) for i in idx) / len(idx) / 100
        out["words"].append({"t": txt, "b": [x0, y0, x1, y1], "c": round(conf, 3)})
    out["text"] = "\n".join(w["t"] for w in out["words"])
    return out


_rapid = None


def run_rapidocr(img: Image.Image, **_: Any) -> Result:
    global _rapid
    from rapidocr import RapidOCR

    if _rapid is None:
        _rapid = RapidOCR()
    r = _rapid(img)
    out = empty()
    if r.boxes is not None:
        for box, txt, sc in zip(r.boxes, r.txts, r.scores):
            xs, ys = [p[0] for p in box], [p[1] for p in box]
            out["words"].append(
                {"t": txt, "b": [min(xs), min(ys), max(xs), max(ys)], "c": round(float(sc), 3)}
            )
    out["words"] = [{**w, "b": [float(v) for v in w["b"]]} for w in out["words"]]
    out["text"] = "\n".join(w["t"] for w in out["words"])
    return out


_doctr = None


def run_doctr(img: Image.Image, **_: Any) -> Result:
    global _doctr
    import numpy as np
    from doctr.models import from_hub, ocr_predictor

    if _doctr is None:
        reco = from_hub("Felix92/doctr-torch-parseq-multilingual-v1")
        _doctr = ocr_predictor(det_arch="db_resnet50", reco_arch=reco, pretrained=True)
    W, H = img.size
    doc = _doctr([np.array(img.convert("RGB"))])
    out = empty()
    for block in doc.pages[0].blocks:
        for line in block.lines:
            (x0, y0), (x1, y1) = line.geometry
            txt = " ".join(w.value for w in line.words)
            conf = sum(w.confidence for w in line.words) / max(1, len(line.words))
            out["words"].append({"t": txt, "b": [x0 * W, y0 * H, x1 * W, y1 * H], "c": round(conf, 3)})
    out["text"] = "\n".join(w["t"] for w in out["words"])
    return out


# ---------------------------------------------------------------- layout / ROI detectors


_det_cache: dict[str, Any] = {}


def _config_fix(repo: str) -> dict:
    """TATR configs carry dilation=null (also nested), which transformers>=5 rejects. Load them fixed."""
    if "table-transformer" not in repo:
        return {}
    from huggingface_hub import hf_hub_download
    from transformers import TableTransformerConfig

    raw = json.load(open(hf_hub_download(repo, "config.json")))

    def fix(d):
        if isinstance(d, dict):
            return {k: (False if k == "dilation" and v is None else fix(v)) for k, v in d.items()}
        return d

    return {"config": TableTransformerConfig.from_dict(fix(raw))}


def _proc_fix(repo: str) -> dict:
    """The TATR structure processor stores only longest_edge; give the sizes the TATR paper uses."""
    if "table-transformer-structure" in repo:
        return {"size": {"shortest_edge": 800, "longest_edge": 1000}}
    return {}


def _hf_detector(repo: str, img: Image.Image, threshold: float) -> list[dict]:
    torch = _torch()
    from transformers import AutoImageProcessor, AutoModelForObjectDetection

    if repo not in _det_cache:
        _det_cache[repo] = (
            AutoImageProcessor.from_pretrained(repo, **_proc_fix(repo)),
            AutoModelForObjectDetection.from_pretrained(repo, **_config_fix(repo)).eval(),
        )
    proc, model = _det_cache[repo]
    inputs = proc(images=img.convert("RGB"), return_tensors="pt")
    with torch.inference_mode():
        o = model(**inputs)
    res = proc.post_process_object_detection(
        o, threshold=threshold, target_sizes=[(img.size[1], img.size[0])]
    )[0]
    regs = []
    for s, lab, box in zip(res["scores"], res["labels"], res["boxes"]):
        regs.append(
            {
                "label": model.config.id2label[int(lab)],
                "b": [round(float(v), 1) for v in box],
                "s": round(float(s), 3),
            }
        )
    return regs


def run_heron(img: Image.Image, **_: Any) -> Result:
    out = empty()
    out["regions"] = _hf_detector("docling-project/docling-layout-heron", img, 0.5)
    return out


def run_ppdoclayout(img: Image.Image, **_: Any) -> Result:
    out = empty()
    out["regions"] = _hf_detector("PaddlePaddle/PP-DocLayoutV3_safetensors", img, 0.5)
    return out


def run_tatr_det(img: Image.Image, **_: Any) -> Result:
    out = empty()
    out["regions"] = _hf_detector("microsoft/table-transformer-detection", img, 0.7)
    return out


_yolo = None


def run_doclayout_yolo(img: Image.Image, **_: Any) -> Result:
    """DocLayout-YOLO. Weights Apache-2.0 but the doclayout_yolo package is AGPL-3.0 (bench only)."""
    global _yolo
    from doclayout_yolo import YOLOv10
    from huggingface_hub import hf_hub_download

    if _yolo is None:
        _yolo = YOLOv10(
            hf_hub_download("juliozhao/DocLayout-YOLO-DocStructBench", "doclayout_yolo_docstructbench_imgsz1024.pt")
        )
    r = _yolo.predict(img.convert("RGB"), imgsz=1024, conf=0.3, device="cpu", verbose=False)[0]
    out = empty()
    for box, c, s in zip(r.boxes.xyxy.tolist(), r.boxes.cls.tolist(), r.boxes.conf.tolist()):
        out["regions"].append({"label": r.names[int(c)], "b": [round(v, 1) for v in box], "s": round(s, 3)})
    return out


# ---------------------------------------------------------------- table structure pipeline


def _cells_from_structure(regs: list[dict], words: list[dict]) -> list[list[str]]:
    rows = sorted([r["b"] for r in regs if r["label"] == "table row"], key=lambda b: b[1])
    cols = sorted([r["b"] for r in regs if r["label"] == "table column"], key=lambda b: b[0])
    grid = [["" for _ in cols] for _ in rows]
    for w in words:
        cx, cy = (w["b"][0] + w["b"][2]) / 2, (w["b"][1] + w["b"][3]) / 2
        ri = next((i for i, b in enumerate(rows) if b[1] <= cy <= b[3]), None)
        ci = next((i for i, b in enumerate(cols) if b[0] <= cx <= b[2]), None)
        if ri is not None and ci is not None:
            grid[ri][ci] = (grid[ri][ci] + " " + w["t"]).strip()
    return [r for r in grid if any(r)]


def run_tatr_pipeline(img: Image.Image, words: list[dict] | None = None, **_: Any) -> Result:
    """Table Transformer detection -> structure recognition on each crop -> words into cells.

    Uses the PDF text layer words (born-digital) when given, else Tesseract words.
    """
    out = empty()
    if not words:
        words = run_tesseract(img)["words"]
    dets = _hf_detector("microsoft/table-transformer-detection", img, 0.7)
    out["regions"] = dets
    for d in dets:
        x0, y0, x1, y1 = d["b"]
        pad = 20
        box = [max(0, x0 - pad), max(0, y0 - pad), min(img.size[0], x1 + pad), min(img.size[1], y1 + pad)]
        crop = img.crop(box)
        regs = _hf_detector("microsoft/table-transformer-structure-recognition-v1.1-all", crop, 0.6)
        for r in regs:
            r["b"] = [r["b"][0] + box[0], r["b"][1] + box[1], r["b"][2] + box[0], r["b"][3] + box[1]]
        inside = [w for w in words if x0 - pad <= (w["b"][0] + w["b"][2]) / 2 <= x1 + pad
                  and y0 - pad <= (w["b"][1] + w["b"][3]) / 2 <= y1 + pad]
        out["tables"].append({"b": d["b"], "rows": _cells_from_structure(regs, inside)})
    out["text"] = "\n".join(" | ".join(r) for t in out["tables"] for r in t["rows"])
    return out


# ---------------------------------------------------------------- Docling (layout + TableFormer)

_docling = None


def run_docling(img: Image.Image, pdf_page: str | None = None, **_: Any) -> Result:
    """Docling standard pipeline (Heron layout + TableFormer accurate) on the one-page PDF; Tesseract on bitmaps."""
    global _docling
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
    from docling.document_converter import DocumentConverter, PdfFormatOption

    if _docling is None:
        from docling.datamodel.pipeline_options import TesseractCliOcrOptions

        # OCR only where the page has no text layer (bitmap areas), as Docling does by default.
        opts = PdfPipelineOptions(do_ocr=True, ocr_options=TesseractCliOcrOptions(lang=["eng", "deu", "fra", "ita"]))
        opts.table_structure_options.mode = TableFormerMode.ACCURATE
        _docling = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)})
    doc = _docling.convert(pdf_page).document
    out = empty()
    out["text"] = doc.export_to_markdown()
    ph = doc.pages[1].size.height

    def px(bb):  # docling bbox bottom-left origin in points -> top-left pixels
        b = bb.to_top_left_origin(page_height=ph)
        return [b.l * SCALE, b.t * SCALE, b.r * SCALE, b.b * SCALE]

    for item, _lvl in doc.iterate_items():
        if item.prov:
            out["regions"].append({"label": str(item.label.value), "b": px(item.prov[0].bbox), "s": 1.0})
            if getattr(item, "text", None):
                out["words"].append({"t": item.text, "b": px(item.prov[0].bbox), "c": 1.0})
    for t in doc.tables:
        rows = [[c.text for c in r] for r in t.data.grid]
        out["tables"].append({"b": px(t.prov[0].bbox) if t.prov else None, "rows": rows})
        for cell in t.data.table_cells:  # every cell keeps its own box: provenance for each fee value
            if cell.bbox is not None and cell.text:
                b = cell.bbox if cell.bbox.coord_origin.value == "TOPLEFT" else cell.bbox.to_top_left_origin(page_height=ph)
                out["words"].append({"t": cell.text, "b": [b.l * SCALE, b.t * SCALE, b.r * SCALE, b.b * SCALE], "c": 1.0})
    return out


# ---------------------------------------------------------------- VLMs (image -> text)

_vlm: dict[str, Any] = {}
MAX_TIME = 600.0  # seconds per generate call


def _load_vlm(repo: str, **kw: Any):
    torch = _torch()
    import transformers
    from transformers import AutoModelForImageTextToText, AutoProcessor

    if repo not in _vlm:
        proc = AutoProcessor.from_pretrained(repo, **kw)
        # LightOnOCR-2's config says mistral3, but its weights use LightOnOCR names: the Auto class
        # silently leaves the vision tower random (the model then "sees" a blank page).
        cls = transformers.LightOnOcrForConditionalGeneration if "LightOnOCR" in repo else AutoModelForImageTextToText
        model = cls.from_pretrained(repo, dtype=torch.bfloat16, **kw).eval()
        _vlm[repo] = (proc, model)
    return _vlm[repo]


def _chat(repo: str, img: Image.Image, prompt: str | None, max_new: int, keep_special: bool = False,
          **kw: Any) -> str:
    torch = _torch()
    proc, model = _load_vlm(repo, **kw)
    content: list[dict] = [{"type": "image", "image": img.convert("RGB")}]
    if prompt:
        content.append({"type": "text", "text": prompt})
    msgs = [{"role": "user", "content": content}]
    inputs = proc.apply_chat_template(
        msgs, add_generation_prompt=True, tokenize=True, return_dict=True, return_tensors="pt"
    )
    inputs = {k: (v.to(torch.bfloat16) if v.dtype.is_floating_point else v) for k, v in inputs.items()}
    with torch.inference_mode():
        # Some repos ship use_cache=false in generation_config: 8x slower decoding on CPU.
        # max_time caps one call on CPU; a cut-off answer is scored as it stands, never padded.
        gen = model.generate(**inputs, max_new_tokens=max_new, do_sample=False, use_cache=True, max_time=MAX_TIME)
    return proc.decode(gen[0][inputs["input_ids"].shape[1]:], skip_special_tokens=not keep_special)


def _fit(img: Image.Image, longest: int) -> Image.Image:
    s = longest / max(img.size)
    return img if s >= 1 else img.resize((int(img.size[0] * s), int(img.size[1] * s)), Image.LANCZOS)


def _vlm_text_result(text: str) -> Result:
    out = empty()
    out["text"] = text
    out["tables"] = parse_tables(text)
    return out


def run_lighton(img: Image.Image, **_: Any) -> Result:
    return _vlm_text_result(_chat("lightonai/LightOnOCR-2-1B", _fit(img, 1540), None, 2048))


def run_glm_ocr(img: Image.Image, **_: Any) -> Result:
    return _vlm_text_result(_chat("zai-org/GLM-OCR", _fit(img, 1540), "Text Recognition:", 2048))


def run_got(img: Image.Image, **_: Any) -> Result:
    torch = _torch()
    repo = "stepfun-ai/GOT-OCR-2.0-hf"
    proc, model = _load_vlm(repo)
    inputs = proc(img.convert("RGB"), return_tensors="pt", format=True)
    inputs = {k: (v.to(torch.bfloat16) if v.dtype.is_floating_point else v) for k, v in inputs.items()}
    with torch.inference_mode():
        gen = model.generate(**inputs, do_sample=False, tokenizer=proc.tokenizer,
                             stop_strings="<|im_end|>", max_new_tokens=2048, max_time=MAX_TIME)
    text = proc.decode(gen[0, inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    return _vlm_text_result(text)


def run_paddleocr_vl(img: Image.Image, **_: Any) -> Result:
    """PaddleOCR-VL 1.6 as designed: PP-DocLayoutV3 regions, then the VLM reads each crop."""
    out = empty()
    regs = _hf_detector("PaddlePaddle/PP-DocLayoutV3_safetensors", img, 0.5)
    regs.sort(key=lambda r: (r["b"][1], r["b"][0]))
    parts = []
    for r in regs:
        lab = r["label"].lower()
        if any(k in lab for k in ("image", "seal", "chart", "figure", "number", "header_image", "footer_image")):
            continue
        task = "Table Recognition:" if "table" in lab else "OCR:"
        x0, y0, x1, y1 = r["b"]
        if (x1 - x0) < 8 or (y1 - y0) < 8:
            continue
        crop = img.crop((max(0, x0 - 4), max(0, y0 - 4), x1 + 4, y1 + 4))
        txt = _chat("PaddlePaddle/PaddleOCR-VL-1.6", crop, task, 1024).strip()
        r["text"] = txt
        out["regions"].append(r)
        if "table" in lab:
            for t in parse_tables(_otsl_to_html(txt)) or [{"b": None, "rows": [[txt]]}]:
                out["tables"].append({"b": r["b"], "rows": t["rows"]})
            out["words"].append({"t": strip_markup(_otsl_to_html(txt)), "b": r["b"], "c": r["s"]})
        else:
            out["words"].append({"t": txt, "b": r["b"], "c": r["s"]})
        parts.append(txt)
    out["text"] = "\n\n".join(parts)
    return out


def _otsl_to_html(s: str) -> str:
    """PaddleOCR-VL tables come as OTSL (<fcel>, <ecel>, <nl>...). Convert to simple HTML rows."""
    if "<fcel>" not in s and "<ecel>" not in s:
        return s
    rows = []
    for line in re.split(r"<nl>", s):
        cells = re.split(r"<(?:fcel|ecel|lcel|ucel|xcel|ched|rhed|srow)>", line)[1:]
        if cells:
            rows.append("<tr>" + "".join(f"<td>{html.escape(c.strip())}</td>" for c in cells) + "</tr>")
    return "<table>" + "".join(rows) + "</table>"


# ---------------------------------------------------------------- granite-docling (DocTags with boxes)


def run_granite_docling(img: Image.Image, **_: Any) -> Result:
    # DocTags (<text>, <loc_n>, <otsl>…) are special tokens: skipping them would return an empty page.
    text = _chat("ibm-granite/granite-docling-258M", img, "Convert this page to docling.", 4096, keep_special=True)
    text = re.sub(r"<end_of_utterance>|<\|end_of_text\|>", "", text)
    out = empty()
    W, H = img.size
    loc = r"<loc_(\d+)><loc_(\d+)><loc_(\d+)><loc_(\d+)>"
    for m in re.finditer(r"<(\w+)>" + loc + r"(.*?)</\1>", text, flags=re.S):
        tag, a, b, c, d, body = m.groups()
        bb = [int(a) / 500 * W, int(b) / 500 * H, int(c) / 500 * W, int(d) / 500 * H]
        out["regions"].append({"label": tag, "b": bb, "s": 1.0})
        if tag == "otsl":
            t = parse_tables(_otsl_to_html(body))
            if t:
                out["tables"].append({"b": bb, "rows": t[0]["rows"]})
            out["words"].append({"t": strip_markup(_otsl_to_html(body)), "b": bb, "c": 1.0})
        else:
            clean = re.sub(r"<[^>]+>", " ", body).strip()
            if clean:
                out["words"].append({"t": clean, "b": bb, "c": 1.0})
    out["text"] = "\n".join(w["t"] for w in out["words"])
    out["raw"] = text
    return out


# ---------------------------------------------------------------- Florence-2 (OCR with regions)


def run_florence2(img: Image.Image, **_: Any) -> Result:
    torch = _torch()
    from transformers import AutoProcessor, Florence2ForConditionalGeneration

    repo = "florence-community/Florence-2-large"
    if repo not in _vlm:
        _vlm[repo] = (
            AutoProcessor.from_pretrained(repo),
            Florence2ForConditionalGeneration.from_pretrained(repo, dtype=torch.bfloat16).eval(),
        )
    proc, model = _vlm[repo]
    out = empty()
    # Florence sees 768x768; tile the page in horizontal strips so small print stays legible.
    W, H = img.size
    strip = W  # square-ish tiles
    y = 0
    while y < H:
        tile = img.crop((0, y, W, min(H, y + strip))).convert("RGB")
        inputs = proc(text="<OCR_WITH_REGION>", images=tile, return_tensors="pt")
        inputs = {k: (v.to(torch.bfloat16) if v.dtype.is_floating_point else v) for k, v in inputs.items()}
        with torch.inference_mode():
            gen = model.generate(**inputs, max_new_tokens=1024, num_beams=3, do_sample=False)
        raw = proc.batch_decode(gen, skip_special_tokens=False)[0]
        parsed = proc.post_process_generation(raw, task="<OCR_WITH_REGION>", image_size=tile.size)
        r = parsed["<OCR_WITH_REGION>"]
        for quad, label in zip(r["quad_boxes"], r["labels"]):
            xs, ys = quad[0::2], quad[1::2]
            t = label.replace("</s>", "").replace("<s>", "").strip()
            if t:
                out["words"].append({"t": t, "b": [min(xs), min(ys) + y, max(xs), max(ys) + y], "c": 1.0})
        y += strip
    out["words"] = [{**w, "b": [float(v) for v in w["b"]]} for w in out["words"]]
    out["text"] = "\n".join(w["t"] for w in out["words"])
    return out


# ---------------------------------------------------------------- Qwen3-VL: direct fee extraction with boxes

FEE_PROMPT = (
    "You read one page of a financial document (fund KID, bank price list, cost report, factsheet, "
    "statement). List every fee, cost, charge or commission figure printed on the page. Copy the label and "
    "the value exactly as printed (keep %, currency, 'p.a.', minimums). Do not compute or guess; skip "
    "anything not printed. Answer only with a JSON array: "
    '[{"label": "...", "value": "...", "bbox_2d": [x1, y1, x2, y2]}] where bbox_2d is the box of the value. '
    "Answer [] if the page has no fee figures."
)


def run_qwen3vl(img: Image.Image, **_: Any) -> Result:
    W, H = img.size
    small = _fit(img, 1280)
    text = _chat("Qwen/Qwen3-VL-2B-Instruct", small, FEE_PROMPT, 1536)
    out = empty()
    out["raw"] = text
    m = re.search(r"\[.*\]", text, flags=re.S)
    items: list = []
    if m:
        try:
            items = json.loads(m.group(0))
        except json.JSONDecodeError:
            items = [json.loads(x) for x in re.findall(r"\{[^{}]*\}", m.group(0)) if _is_json(x)]
    for it in items:
        if not isinstance(it, dict):
            continue
        b = it.get("bbox_2d")
        bb = None
        if isinstance(b, list) and len(b) == 4 and all(isinstance(v, (int, float)) for v in b):
            bb = [b[0] / 1000 * W, b[1] / 1000 * H, b[2] / 1000 * W, b[3] / 1000 * H]  # Qwen3 grid 0..1000
        out["fees"].append({"label": str(it.get("label", "")), "value": str(it.get("value", "")), "b": bb})
    out["text"] = "\n".join(f"{f['label']}: {f['value']}" for f in out["fees"])
    return out


def _is_json(s: str) -> bool:
    try:
        json.loads(s)
        return True
    except json.JSONDecodeError:
        return False


# ---------------------------------------------------------------- LayoutLM document QA

DOCQA_QUESTIONS = {
    "ongoing": "What are the ongoing costs?",
    "entry": "What is the entry cost?",
    "exit": "What is the exit cost?",
    "transaction": "What are the transaction costs?",
    "performance": "What is the performance fee?",
    "custody": "What is the custody fee?",
    "management": "What is the management fee?",
    "brokerage": "What is the brokerage commission?",
}

_docqa = None


def run_layoutlm_docqa(img: Image.Image, **_: Any) -> Result:
    global _docqa
    from transformers import pipeline

    if _docqa is None:
        _docqa = pipeline("document-question-answering", model="impira/layoutlm-document-qa", device="cpu")
    out = empty()
    words = None
    for key, q in DOCQA_QUESTIONS.items():
        kw = {"word_boxes": words} if words else {}
        ans = _docqa(image=img.convert("RGB"), question=q, top_k=1, **kw)
        if ans and ans[0]["score"] > 0.3:
            out["fees"].append({"label": key, "value": ans[0]["answer"], "b": None, "s": round(ans[0]["score"], 3)})
    out["text"] = "\n".join(f"{f['label']}: {f['value']}" for f in out["fees"])
    return out


# ---------------------------------------------------------------- baseline: the PDF text layer


def run_pdfplumber(img: Image.Image, pdf_page: str | None = None, **_: Any) -> Result:
    """Current FeeLens engine: pdfplumber words and tables (born-digital only, no model)."""
    import pdfplumber

    out = empty()
    with pdfplumber.open(pdf_page) as pdf:
        p = pdf.pages[0]
        lines: dict[int, list] = {}
        for w in p.extract_words(keep_blank_chars=False, use_text_flow=False):
            lines.setdefault(round(w["top"] / 3), []).append(w)
        for ws in lines.values():
            ws.sort(key=lambda w: w["x0"])
            out["words"].append({
                "t": " ".join(w["text"] for w in ws),
                "b": [min(w["x0"] for w in ws) * SCALE, min(w["top"] for w in ws) * SCALE,
                      max(w["x1"] for w in ws) * SCALE, max(w["bottom"] for w in ws) * SCALE],
                "c": 1.0,
            })
        for t in p.find_tables():
            rows = [[(c or "").replace("\n", " ") for c in r] for r in t.extract()]
            out["tables"].append({"b": [v * SCALE for v in t.bbox], "rows": rows})
        out["text"] = p.extract_text() or ""
    return out


MODELS: dict[str, dict[str, Any]] = {
    # key: fn, family, HF repo(s), licence, needs (pdf/words)
    "pdfplumber": {"fn": run_pdfplumber, "family": "baseline", "repo": "(pdfplumber, no model)", "licence": "MIT"},
    "tesseract": {"fn": run_tesseract, "family": "ocr", "repo": "tesseract-ocr 5 (eng,deu,fra,ita)", "licence": "Apache-2.0"},
    "rapidocr": {"fn": run_rapidocr, "family": "ocr", "repo": "RapidOCR (PP-OCRv5 ONNX)", "licence": "Apache-2.0"},
    "doctr": {"fn": run_doctr, "family": "ocr", "repo": "Felix92/doctr-torch-parseq-multilingual-v1", "licence": "Apache-2.0"},
    "florence2": {"fn": run_florence2, "family": "ocr", "repo": "florence-community/Florence-2-large", "licence": "MIT"},
    "heron": {"fn": run_heron, "family": "layout", "repo": "docling-project/docling-layout-heron", "licence": "Apache-2.0"},
    "ppdoclayout3": {"fn": run_ppdoclayout, "family": "layout", "repo": "PaddlePaddle/PP-DocLayoutV3_safetensors", "licence": "Apache-2.0"},
    "doclayout_yolo": {"fn": run_doclayout_yolo, "family": "layout", "repo": "juliozhao/DocLayout-YOLO-DocStructBench", "licence": "weights Apache-2.0, code AGPL-3.0"},
    "tatr": {"fn": run_tatr_pipeline, "family": "table", "repo": "microsoft/table-transformer-detection + structure-recognition-v1.1-all", "licence": "MIT"},
    "docling": {"fn": run_docling, "family": "table", "repo": "docling-project/docling-models (Heron + TableFormer)", "licence": "MIT / Apache-2.0 / CDLA-2.0"},
    "granite_docling": {"fn": run_granite_docling, "family": "vlm", "repo": "ibm-granite/granite-docling-258M", "licence": "Apache-2.0"},
    "paddleocr_vl": {"fn": run_paddleocr_vl, "family": "vlm", "repo": "PaddlePaddle/PaddleOCR-VL-1.6 (+PP-DocLayoutV3)", "licence": "Apache-2.0"},
    "glm_ocr": {"fn": run_glm_ocr, "family": "vlm", "repo": "zai-org/GLM-OCR", "licence": "MIT"},
    "lighton_ocr": {"fn": run_lighton, "family": "vlm", "repo": "lightonai/LightOnOCR-2-1B", "licence": "Apache-2.0"},
    "got_ocr": {"fn": run_got, "family": "vlm", "repo": "stepfun-ai/GOT-OCR-2.0-hf", "licence": "Apache-2.0"},
    "qwen3vl": {"fn": run_qwen3vl, "family": "vlm-extract", "repo": "Qwen/Qwen3-VL-2B-Instruct", "licence": "Apache-2.0"},
    "layoutlm_docqa": {"fn": run_layoutlm_docqa, "family": "docqa", "repo": "impira/layoutlm-document-qa", "licence": "MIT"},
}

RUNNERS: dict[str, Callable[..., Result]] = {k: v["fn"] for k, v in MODELS.items()}
