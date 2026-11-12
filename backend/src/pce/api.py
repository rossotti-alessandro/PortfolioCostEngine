"""FastAPI application. Local-first: no outbound network calls anywhere in request handling.

Every /api route needs a signed-in session (pce.security). Tenant and user come from the
account, never from the client; X-Role only picks among the roles the account holds (the demo
role switch). Every query is filtered by tenant. See docs/app/SECURITY.md.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import time
import zipfile
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import __version__, security
from .analysis import analyse
from .crm.router import router as crm_router
from .db import (
    Approval,
    AuditEvent,
    Document,
    FactRow,
    ProposalVersion,
    Prospect,
    RequestState,
    Review,
    data_dir,
    make_session_factory,
)
from .demo import spec
from .extraction.models import DOC_TYPE_LABELS, DocType
from .extraction.parsers import PARSERS, classify, extract
from .extraction.vocab import FEE_LABEL_NAMES, load_taxonomy
from .finance.money import D
from .pipeline_view import document_pipeline
from .review_points import review_points

MAX_UPLOAD_BYTES = 25 * 1024 * 1024
MAX_XLSX_UNCOMPRESSED = 100 * 1024 * 1024
MAX_FILES_PER_UPLOAD = 20
ALLOWED = {
    ".pdf": "application/pdf",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

app = FastAPI(title="PortfolioCostEngine API", version=__version__)
app.add_middleware(security.SecurityMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(security.router)
app.include_router(crm_router)
SessionFactory = make_session_factory()


def get_db():
    s = SessionFactory()
    try:
        yield s
    finally:
        s.close()


class Ctx(BaseModel):
    tenant: str
    user: str
    role: str


def ctx(request: Request, x_role: Annotated[str | None, Header()] = None) -> Ctx:
    acc = getattr(request.state, "account", None)
    if acc is None:  # the middleware sets it on every gated route; refuse if a route slipped past
        raise HTTPException(401, "sign in required")
    role = x_role or ("analyst" if "analyst" in acc.roles else acc.roles[0])
    if role not in acc.roles:
        raise HTTPException(403, "role not allowed for this account")
    return Ctx(tenant=acc.tenant, user=acc.username, role=role)


DB = Annotated[Session, Depends(get_db)]
C = Annotated[Ctx, Depends(ctx)]


def audit(db: Session, c: Ctx, prospect_id: int | None, action: str, **detail: Any) -> None:
    db.add(AuditEvent(tenant_id=c.tenant, prospect_id=prospect_id, user=c.user, action=action, detail=detail))


def get_prospect(db: Session, c: Ctx, pid: int) -> Prospect:
    p = db.scalar(select(Prospect).where(Prospect.id == pid, Prospect.tenant_id == c.tenant))
    if not p:
        raise HTTPException(404, "prospect not found")  # same answer for other tenants: no existence leak
    return p


def fact_out(f: FactRow) -> dict:
    return {
        "id": f.id,
        "document_id": f.document_id,
        "key": f.key,
        "kind": f.kind,
        "field": f.field,
        "label": f.label,
        "value": f.value_current,
        "value_extracted": f.value_extracted,
        "currency": f.currency,
        "isin": f.isin,
        "fee_code": f.fee_code,
        "fee_label": FEE_LABEL_NAMES.get(f.fee_code or "", None),
        "measurement": f.measurement,
        "extra": f.extra,
        "evidence": f.evidence,
        "status": f.status,
    }


def doc_out(d: Document, n_facts: int = 0) -> dict:
    dt = d.doc_type_override or d.doc_type
    return {
        "id": d.id,
        "filename": d.filename,
        "sha256": d.sha256,
        "size": d.size,
        "media_type": d.media_type,
        "doc_type": dt,
        "doc_type_label": DOC_TYPE_LABELS.get(DocType(dt), dt),
        "detected_type": d.doc_type,
        "profile": d.profile,
        "pages": d.pages,
        "status": d.status,
        "uploaded_at": d.uploaded_at,
        "uploaded_by": d.uploaded_by,
        "extractor_version": d.extractor_version,
        "fact_count": n_facts,
    }


def compute(db: Session, c: Ctx, p: Prospect) -> dict:
    docs = db.scalars(
        select(Document).where(Document.prospect_id == p.id, Document.tenant_id == c.tenant)
    ).all()
    facts = (
        db.scalars(
            select(FactRow).where(
                FactRow.tenant_id == c.tenant, FactRow.document_id.in_([d.id for d in docs])
            )
        ).all()
        if docs
        else []
    )
    result = analyse(
        {"domicile": p.domicile, "base_ccy": p.base_ccy},
        [
            {
                "id": d.id,
                "filename": d.filename,
                "doc_type": d.doc_type_override or d.doc_type,
                "profile": d.profile,
            }
            for d in docs
        ],
        [{**fact_out(f), "value": f.value_current} for f in facts],
        p.proposal or spec.PROPOSAL_DEFAULTS,
    )
    fmap = {f.id: f for f in facts}
    dmap = {d.id: d for d in docs}

    def where(f: FactRow) -> str:
        ev = f.evidence or {}
        loc = f"p.{ev['page']}" if ev.get("page") else f"{ev.get('sheet')}!{ev.get('cell')}"
        return f"{dmap[f.document_id].filename} {loc}"

    def sources(ids: list[int]) -> list[str]:
        return [where(fmap[i]) for i in ids if i in fmap]

    def provenance(fid: int, role: str) -> dict:
        """Everything the trace view needs to show one input without another request."""
        f = fmap[fid]
        ev = f.evidence or {}
        return {
            "fact_id": f.id,
            "role": "fx_rate" if f.field == "fx_rate" else role,
            "document_id": f.document_id,
            "filename": dmap[f.document_id].filename,
            "where": where(f),
            "field": f.field,
            "label": f.label,
            "value": f.value_current,
            "value_extracted": f.value_extracted,
            "currency": f.currency,
            "status": f.status,
            "review": (f.extra or {}).get("review"),
            **{
                k: ev.get(k)
                for k in (
                    "page",
                    "bbox",
                    "page_width",
                    "page_height",
                    "sheet",
                    "cell",
                    "snippet",
                    "engine",
                    "confidence",
                    "row_bbox",
                    "label_bbox",
                    "region",
                )
            },
        }

    # a product cost is rate x holding value: the holding line is the basis input
    holding_fact = {(h["institution"], h["isin"]): h["fact_id"] for h in result["holdings"] if h["isin"]}

    def enrich(ledger: dict) -> None:
        for a in ledger["atoms"]:
            a["evidence_sources"] = sources(a["evidence_fact_ids"])
            ev = [provenance(i, "value") for i in a["evidence_fact_ids"] if i in fmap]
            basis = holding_fact.get((a["institution"], a["instrument_id"]))
            if a["basis_amount"] is not None and basis in fmap:
                ev.append(provenance(basis, "basis"))
            a["evidence"] = ev

    enrich(result["current"])
    enrich(result["scenarios"]["current_comparable"])
    enrich(result["scenarios"]["same_holdings"]["ledger"])
    enrich(result["scenarios"]["optimized"]["ledger"])
    for chk in result["checks"]:
        chk["sources"] = sources(chk["fact_ids"])
        chk["evidence"] = [provenance(i, "value") for i in chk["fact_ids"] if i in fmap]
    result["unused_mentions"] = [
        provenance(f.id, "value") for f in facts if f.kind == "fee_mention" and f.status != "rejected"
    ]
    result["review_points"] = review_points(result)
    result["documents"] = [
        {"id": d.id, "filename": d.filename, "doc_type": d.doc_type_override or d.doc_type} for d in docs
    ]
    states = {
        r.key: r.status
        for r in db.scalars(
            select(RequestState).where(RequestState.prospect_id == p.id, RequestState.tenant_id == c.tenant)
        )
    }
    for r in result["requests"]:
        r["status"] = states.get(r["key"], "open")
    reviewed = sum(1 for f in facts if f.status in ("accepted", "corrected", "manual"))
    result["review"] = {
        "facts": len(facts),
        "reviewed": reviewed,
        "rejected": sum(1 for f in facts if f.status == "rejected"),
    }
    snapshot = json.dumps({k: result[k] for k in ("current", "scenarios")}, sort_keys=True)
    result["snapshot_hash"] = hashlib.sha256(snapshot.encode()).hexdigest()
    appr = db.scalars(
        select(Approval)
        .where(Approval.prospect_id == p.id, Approval.tenant_id == c.tenant)
        .order_by(Approval.id.desc())
    ).first()
    result["approval"] = (
        None
        if not appr
        else {
            "user": appr.user,
            "role": appr.role,
            "at": appr.at,
            "note": appr.note,
            "valid": appr.snapshot_hash == result["snapshot_hash"],
        }
    )
    result["prospect"] = {
        "id": p.id,
        "code": p.code,
        "label": p.label,
        "domicile": p.domicile,
        "synthetic": p.synthetic,
    }
    return result


def safe_filename(name: str) -> str:
    """Keep the base name only, drop control and path characters, cap the length."""
    base = Path(name.replace("\\", "/")).name
    clean = "".join(ch for ch in base if ch.isprintable() and ch not in '<>:"/\\|?*').strip(" .")
    return (clean or "upload")[-150:]


def sniffed_type(data: bytes) -> str:
    import magic  # libmagic: the bytes decide, not the extension

    return magic.from_buffer(data[:8192], mime=True)


def ingest(db: Session, c: Ctx, p: Prospect, filename: str, data: bytes) -> tuple[Document, bool]:
    filename = safe_filename(filename)
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED:
        raise HTTPException(415, f"{filename}: only PDF and XLSX are accepted")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"{filename}: larger than {MAX_UPLOAD_BYTES // 1024 // 1024} MB")
    if suffix == ".pdf" and (not data.startswith(b"%PDF") or sniffed_type(data) != "application/pdf"):
        raise HTTPException(415, f"{filename}: not a PDF file")
    if suffix == ".xlsx" and sniffed_type(data) not in (ALLOWED[".xlsx"], "application/zip"):
        raise HTTPException(415, f"{filename}: not an XLSX file")
    if suffix == ".xlsx":
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                if sum(i.file_size for i in z.infolist()) > MAX_XLSX_UNCOMPRESSED:
                    raise HTTPException(413, f"{filename}: spreadsheet expands too much (possible zip bomb)")
                if any(n.endswith(".bin") and "vbaProject" in n for n in z.namelist()):
                    raise HTTPException(415, f"{filename}: macro-enabled content is not accepted")
        except zipfile.BadZipFile as exc:
            raise HTTPException(415, f"{filename}: not a valid XLSX file") from exc
    t0 = time.perf_counter()
    sha = hashlib.sha256(data).hexdigest()
    existing = db.scalar(
        select(Document).where(
            Document.tenant_id == c.tenant, Document.prospect_id == p.id, Document.sha256 == sha
        )
    )
    if existing:
        return existing, False
    store = data_dir() / "storage" / c.tenant
    store.mkdir(parents=True, exist_ok=True)
    path = store / f"{sha}{suffix}"
    if not path.exists():
        path.write_bytes(data)
    stored_ms = round((time.perf_counter() - t0) * 1000)
    try:
        res, pages = extract(filename, data)
    except ValueError as exc:
        raise HTTPException(422, f"{filename}: {exc}") from exc
    res.profile.timings_ms = {"upload": stored_ms, **res.profile.timings_ms}
    doc = Document(
        tenant_id=c.tenant,
        prospect_id=p.id,
        filename=filename,
        sha256=sha,
        size=len(data),
        media_type=ALLOWED[suffix],
        storage_path=str(path),
        doc_type=res.profile.doc_type.value,
        profile=res.profile.model_dump(),
        extractor_version=res.extractor_version,
        pages=[
            {"number": pg.number, "width": pg.width, "height": pg.height, "engine": pg.engine} for pg in pages
        ],
        status="needs_review"
        if res.profile.doc_type == DocType.UNKNOWN or res.profile.warnings
        else "extracted",
        uploaded_by=c.user,
    )
    db.add(doc)
    db.flush()
    for f in res.facts:
        db.add(
            FactRow(
                tenant_id=c.tenant,
                document_id=doc.id,
                key=f.key,
                kind=f.kind,
                field=f.field,
                label=f.label,
                value_extracted=f.value,
                value_current=f.value,
                currency=f.currency,
                isin=f.isin,
                fee_code=f.fee_code,
                measurement=f.measurement,
                extra=f.extra,
                evidence=f.evidence.model_dump(),
            )
        )
    audit(
        db,
        c,
        p.id,
        "document.uploaded",
        filename=filename,
        sha256=sha,
        doc_type=doc.doc_type,
        facts=len(res.facts),
    )
    return doc, True


# ------------------------------------------------------------------ routes
@app.get("/api/health")
def health() -> dict:
    import shutil

    return {
        "status": "ok",
        "version": __version__,
        "ocr": bool(shutil.which("tesseract")),
        "network_calls": "none",
    }


@app.get("/api/taxonomy")
def taxonomy() -> dict:
    """Data catalogue: every document type and fee code we know, and which ones the demo parses today."""
    parsed = {
        "portfolio_statement",
        "cash_statement",
        "annual_cost_report",
        "custody_tariff",
        "general_price_list",
        "kid_priips",
        "kid_finsa",
        "sp_termsheet",
    }  # taxonomy codes covered by PARSERS
    return {
        "fee_labels": FEE_LABEL_NAMES,
        "doc_types": {k.value: v for k, v in DOC_TYPE_LABELS.items()},
        "document_types": [
            {**r, "parser": r["document_type"] in parsed} for r in load_taxonomy("document_types")
        ],
        "fees": load_taxonomy("fee_taxonomy"),
        "public_sources": load_taxonomy("public_sources", "reference"),
    }


class ProspectIn(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=200)
    domicile: str = Field(default="CH", min_length=2, max_length=2)


@app.get("/api/prospects")
def list_prospects(db: DB, c: C) -> list[dict]:
    out = []
    for p in db.scalars(select(Prospect).where(Prospect.tenant_id == c.tenant).order_by(Prospect.id.desc())):
        docs = db.scalars(
            select(Document).where(Document.prospect_id == p.id, Document.tenant_id == c.tenant)
        ).all()
        summary = None
        if docs:
            r = compute(db, c, p)
            summary = {
                "aum": r["aum"]["total"],
                "current_known": r["current"]["total_known"],
                "current_bps": r["current"]["total_bps"],
                "complete": r["current"]["is_complete"],
                "open_requests": sum(1 for q in r["requests"] if q["status"] == "open"),
                "saving": r["scenarios"]["same_holdings"]["comparison"]["annual_saving"],
                "bound": r["scenarios"]["same_holdings"]["comparison"]["bound"],
                "approved": bool(r["approval"] and r["approval"]["valid"]),
            }
        out.append(
            {
                "id": p.id,
                "code": p.code,
                "label": p.label,
                "domicile": p.domicile,
                "synthetic": p.synthetic,
                "created_at": p.created_at,
                "documents": len(docs),
                "summary": summary,
            }
        )
    return out


@app.post("/api/prospects", status_code=201)
def create_prospect(body: ProspectIn, db: DB, c: C) -> dict:
    if db.scalar(select(Prospect).where(Prospect.tenant_id == c.tenant, Prospect.code == body.code)):
        raise HTTPException(409, "a prospect with this code already exists")
    p = Prospect(
        tenant_id=c.tenant,
        code=body.code,
        label=body.label,
        domicile=body.domicile.upper(),
        proposal=json.loads(json.dumps(spec.PROPOSAL_DEFAULTS)),
    )
    db.add(p)
    db.flush()
    audit(db, c, p.id, "prospect.created", code=p.code)
    db.commit()
    return {"id": p.id}


class ProspectPatch(BaseModel):
    label: str | None = None
    domicile: str | None = Field(default=None, min_length=2, max_length=2)


@app.patch("/api/prospects/{pid}")
def patch_prospect(pid: int, body: ProspectPatch, db: DB, c: C) -> dict:
    p = get_prospect(db, c, pid)
    before = {"label": p.label, "domicile": p.domicile}
    if body.label:
        p.label = body.label
    if body.domicile:
        p.domicile = body.domicile.upper()
    audit(db, c, p.id, "prospect.updated", before=before, after={"label": p.label, "domicile": p.domicile})
    db.commit()
    return {"ok": True}


@app.post("/api/demo/seed")
def seed_demo(db: DB, c: C) -> dict:
    """Create the SYNTHETIC demo prospects from data/synthetic (regenerated if missing).

    P-1042: two Swiss/EU banks. P-2077: an Italian bank (EUR) and a US-style broker (USD), plus the real
    public iShares KID when it has been fetched (python -m pce.demo.public_corpus): public, not client data.
    """
    from .demo import archetypes, public_corpus
    from .demo.generate import generate

    root = Path(__file__).resolve().parents[3] / "data" / "synthetic"
    plans = [
        (
            spec.PROSPECT_CODE,
            spec.PROSPECT_LABEL,
            spec.CLIENT_DOMICILE,
            root / "prospect_p1042",
            generate,
            [],
        ),
        (
            archetypes.PROSPECT_CODE,
            archetypes.PROSPECT_LABEL,
            archetypes.CLIENT_DOMICILE,
            root / "prospect_p2077",
            archetypes.generate,
            [public_corpus.TARGET / "kid_IE00B4L5Y983.pdf"],
        ),
    ]
    ids, added = [], 0
    for code, label, domicile, folder, gen, extras in plans:
        if not folder.exists() or not any(folder.iterdir()):
            gen(folder)
        p = db.scalar(select(Prospect).where(Prospect.tenant_id == c.tenant, Prospect.code == code))
        if not p:
            p = Prospect(
                tenant_id=c.tenant,
                code=code,
                label=label,
                domicile=domicile,
                synthetic=True,
                proposal=json.loads(json.dumps(spec.PROPOSAL_DEFAULTS)),
            )
            db.add(p)
            db.flush()
            audit(db, c, p.id, "prospect.created", code=p.code, synthetic=True)
        files = [f for f in sorted(folder.iterdir()) if f.is_file()] + [f for f in extras if f.exists()]
        for f in files:
            if f.suffix in ALLOWED:
                _d, new = ingest(db, c, p, f.name, f.read_bytes())
                added += int(new)
        ids.append(p.id)
    db.commit()
    return {"id": ids[0], "ids": ids, "documents_added": added}


@app.get("/api/prospects/{pid}")
def get_one(pid: int, db: DB, c: C) -> dict:
    p = get_prospect(db, c, pid)
    return {"id": p.id, "code": p.code, "label": p.label, "domicile": p.domicile, "synthetic": p.synthetic}


@app.post("/api/prospects/{pid}/documents")
def upload(pid: int, db: DB, c: C, files: Annotated[list[UploadFile], File()]) -> dict:
    # plain def: FastAPI runs it in its thread pool, so a long OCR does not block other requests (SC-5.11)
    p = get_prospect(db, c, pid)
    if len(files) > MAX_FILES_PER_UPLOAD:
        raise HTTPException(413, f"at most {MAX_FILES_PER_UPLOAD} files per upload")
    out = []
    for uf in files:
        data = uf.file.read(MAX_UPLOAD_BYTES + 1)
        try:
            d, new = ingest(db, c, p, uf.filename or "upload", data)
            out.append(
                {
                    "filename": uf.filename,
                    "status": "duplicate" if not new else d.status,
                    "document_id": d.id,
                    "doc_type": d.doc_type,
                }
            )
        except HTTPException as exc:
            out.append({"filename": uf.filename, "status": "rejected", "error": exc.detail})
    db.commit()
    return {"results": out}


@app.get("/api/prospects/{pid}/documents")
def list_documents(pid: int, db: DB, c: C) -> list[dict]:
    p = get_prospect(db, c, pid)
    docs = db.scalars(
        select(Document).where(Document.prospect_id == p.id, Document.tenant_id == c.tenant)
    ).all()
    counts = {
        d.id: len(db.scalars(select(FactRow.id).where(FactRow.document_id == d.id)).all()) for d in docs
    }
    return [doc_out(d, counts[d.id]) for d in docs]


def get_doc(db: Session, c: Ctx, did: int) -> Document:
    d = db.scalar(select(Document).where(Document.id == did, Document.tenant_id == c.tenant))
    if not d:
        raise HTTPException(404, "document not found")
    return d


@app.get("/api/documents/{did}/file")
def document_file(did: int, db: DB, c: C):
    d = get_doc(db, c, did)
    return FileResponse(
        d.storage_path,
        media_type=d.media_type,
        filename=d.filename,
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


@app.get("/api/documents/{did}/sheet")
def document_sheet(did: int, db: DB, c: C) -> dict:
    """Spreadsheet preview as a cell grid (values as text) so the UI can highlight a cell."""
    from openpyxl import load_workbook

    d = get_doc(db, c, did)
    if not d.filename.lower().endswith(".xlsx"):
        raise HTTPException(400, "not a spreadsheet")
    wb = load_workbook(d.storage_path, data_only=True, read_only=True)
    sheets = []
    for ws in wb.worksheets:
        rows = []
        for r in ws.iter_rows(max_row=200, max_col=26):
            rows.append([None if c_.value is None else str(c_.value) for c_ in r])
        sheets.append({"name": ws.title, "rows": rows})
    return {"sheets": sheets}


@app.get("/api/documents/{did}/facts")
def document_facts(did: int, db: DB, c: C) -> list[dict]:
    d = get_doc(db, c, did)
    return [
        fact_out(f)
        for f in db.scalars(select(FactRow).where(FactRow.document_id == d.id).order_by(FactRow.id))
    ]


class DocPatch(BaseModel):
    doc_type: DocType


@app.get("/api/documents/{did}/pipeline")
def document_pipeline_view(did: int, db: DB, c: C) -> dict:
    """Every processing stage for one document: status, timing, warnings and what it produced."""
    d = get_doc(db, c, did)
    p = get_prospect(db, c, d.prospect_id)
    facts = db.scalars(
        select(FactRow).where(FactRow.document_id == d.id, FactRow.tenant_id == c.tenant)
    ).all()
    return document_pipeline(d, list(facts), client_safe(compute(db, c, p)), p.base_ccy)


@app.patch("/api/documents/{did}")
def set_doc_type(did: int, body: DocPatch, db: DB, c: C) -> dict:
    """Manual reclassification: re-run the matching parser on the stored file."""
    from .extraction.layout import read_pdf

    d = get_doc(db, c, did)
    before = d.doc_type_override or d.doc_type
    d.doc_type_override = body.doc_type.value
    if d.filename.lower().endswith(".pdf") and body.doc_type in PARSERS:
        pages = read_pdf(Path(d.storage_path).read_bytes())
        prof = classify(pages)
        prof.doc_type = body.doc_type
        facts = PARSERS[body.doc_type](pages, prof)
        for old in db.scalars(
            select(FactRow).where(FactRow.document_id == d.id, FactRow.status == "extracted")
        ):
            db.delete(old)
        for f in facts:
            db.add(
                FactRow(
                    tenant_id=c.tenant,
                    document_id=d.id,
                    key=f.key,
                    kind=f.kind,
                    field=f.field,
                    label=f.label,
                    value_extracted=f.value,
                    value_current=f.value,
                    currency=f.currency,
                    isin=f.isin,
                    fee_code=f.fee_code,
                    measurement=f.measurement,
                    extra=f.extra,
                    evidence=f.evidence.model_dump(),
                )
            )
        d.profile = {**prof.model_dump(), "doc_type": body.doc_type.value}
    d.status = "extracted"
    audit(
        db,
        c,
        d.prospect_id,
        "document.reclassified",
        document_id=d.id,
        before=before,
        after=body.doc_type.value,
    )
    db.commit()
    return {"ok": True}


class ReviewIn(BaseModel):
    action: str = Field(pattern="^(accept|correct|reject|reset)$")
    value: str | None = None
    reason: str = ""


@app.post("/api/facts/{fid}/review")
def review_fact(fid: int, body: ReviewIn, db: DB, c: C) -> dict:
    f = db.scalar(select(FactRow).where(FactRow.id == fid, FactRow.tenant_id == c.tenant))
    if not f:
        raise HTTPException(404, "fact not found")
    old = f.value_current
    if body.action == "correct":
        if body.value is None:
            raise HTTPException(422, "a corrected value is required")
        try:
            D(body.value.replace("'", ""))
        except (ValueError, TypeError) as exc:
            raise HTTPException(422, "value must be a number like 1234.50") from exc
        if not body.reason.strip():
            raise HTTPException(422, "a reason is required for a correction")
        f.value_current = str(D(body.value.replace("'", "")))
        f.status = "corrected"
    elif body.action == "accept":
        f.status = "accepted"
    elif body.action == "reject":
        if not body.reason.strip():
            raise HTTPException(422, "a reason is required to reject a value")
        f.status = "rejected"
    else:
        f.status, f.value_current = "extracted", f.value_extracted
    db.add(
        Review(
            tenant_id=c.tenant,
            fact_id=f.id,
            action=body.action,
            old_value=old,
            new_value=f.value_current,
            reason=body.reason,
            user=c.user,
        )
    )
    doc = db.get(Document, f.document_id)
    audit(
        db,
        c,
        doc.prospect_id if doc else None,
        f"fact.{body.action}",
        fact_id=f.id,
        label=f.label,
        old=old,
        new=f.value_current,
        reason=body.reason,
    )
    db.commit()
    return fact_out(f)


@app.get("/api/facts/{fid}/history")
def fact_history(fid: int, db: DB, c: C) -> list[dict]:
    rows = db.scalars(
        select(Review).where(Review.fact_id == fid, Review.tenant_id == c.tenant).order_by(Review.id)
    )
    return [
        {
            "action": r.action,
            "old": r.old_value,
            "new": r.new_value,
            "reason": r.reason,
            "user": r.user,
            "at": r.at,
        }
        for r in rows
    ]


@app.get("/api/prospects/{pid}/analysis")
def analysis(pid: int, db: DB, c: C) -> dict:
    p = get_prospect(db, c, pid)
    return client_safe(compute(db, c, p))  # internal economics only via /internal with an authorised role


def client_safe(r: dict) -> dict:
    """Drop internal economics: the computed margin and the firm's cost and minimum-margin inputs."""
    r.pop("internal", None)
    if "proposal_inputs" in r:  # copy: the inputs may be shared with the stored proposal
        r["proposal_inputs"] = {k: v for k, v in r["proposal_inputs"].items() if k != "internal"}
    return r


@app.get("/api/prospects/{pid}/internal")
def internal(pid: int, db: DB, c: C) -> dict:
    if c.role not in ("senior", "relationship_manager"):
        raise HTTPException(403, "internal economics are restricted to senior and relationship-manager roles")
    p = get_prospect(db, c, pid)
    r = compute(db, c, p)
    audit(db, c, p.id, "internal.viewed")
    db.commit()
    return {
        "internal": r["internal"],
        "same_holdings": r["scenarios"]["same_holdings"]["comparison"],
        "current_complete": r["current"]["is_complete"],
        "requests": r["requests"],
        "proposal_inputs": r["proposal_inputs"],
        "synthetic": r["synthetic"],
    }


@app.get("/api/prospects/{pid}/proposal")
def get_proposal(pid: int, db: DB, c: C) -> dict:
    p = get_prospect(db, c, pid)
    versions = db.scalars(
        select(ProposalVersion)
        .where(ProposalVersion.prospect_id == p.id, ProposalVersion.tenant_id == c.tenant)
        .order_by(ProposalVersion.id.desc())
    )
    return {
        "config": p.proposal or spec.PROPOSAL_DEFAULTS,
        "history": [
            {"version": v.version, "user": v.user, "at": v.at, "summary": v.summary} for v in versions
        ],
    }


@app.put("/api/prospects/{pid}/proposal")
def put_proposal(pid: int, body: dict, db: DB, c: C) -> dict:
    p = get_prospect(db, c, pid)
    cfg = {**(p.proposal or spec.PROPOSAL_DEFAULTS), **body}
    try:  # validate by running the calculation before saving
        for u, r in cfg["eam_tiers"]:
            D(r)
            if u not in (None, ""):
                D(u)
        for k in (
            "custody_bps",
            "custody_min",
            "brokerage_bps",
            "fx_bps",
            "annual_turnover_chf",
            "fx_notional_chf",
            "vat_pct",
        ):
            if D(cfg[k]) < 0:
                raise ValueError(k)
    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(422, f"invalid proposal input: {exc}") from exc
    p.proposal = cfg
    db.flush()
    r = compute(db, c, p)
    n = len(db.scalars(select(ProposalVersion.id).where(ProposalVersion.prospect_id == p.id)).all()) + 1
    same = r["scenarios"]["same_holdings"]["comparison"]
    db.add(
        ProposalVersion(
            tenant_id=c.tenant,
            prospect_id=p.id,
            version=n,
            config=cfg,
            user=c.user,
            summary={
                "proposal_known": same["proposal_known"],
                "annual_saving": same["annual_saving"],
                "bound": same["bound"],
            },
        )
    )
    audit(db, c, p.id, "proposal.saved", version=n)
    db.commit()
    return {"version": n}


class RequestPatch(BaseModel):
    status: str = Field(pattern="^(open|sent|waived)$")


@app.patch("/api/prospects/{pid}/requests/{key:path}")
def patch_request(pid: int, key: str, body: RequestPatch, db: DB, c: C) -> dict:
    p = get_prospect(db, c, pid)
    row = db.scalar(
        select(RequestState).where(
            RequestState.prospect_id == p.id, RequestState.tenant_id == c.tenant, RequestState.key == key
        )
    )
    if row:
        row.status = body.status
    else:
        db.add(RequestState(tenant_id=c.tenant, prospect_id=p.id, key=key, status=body.status))
    audit(db, c, p.id, "request.status", key=key, status=body.status)
    db.commit()
    return {"ok": True}


class ApprovalIn(BaseModel):
    note: str = ""


@app.post("/api/prospects/{pid}/approve")
def approve(pid: int, body: ApprovalIn, db: DB, c: C) -> dict:
    if c.role != "senior":
        raise HTTPException(403, "only a senior reviewer can approve a client report")
    p = get_prospect(db, c, pid)
    r = compute(db, c, p)
    db.add(
        Approval(
            tenant_id=c.tenant,
            prospect_id=p.id,
            user=c.user,
            role=c.role,
            snapshot_hash=r["snapshot_hash"],
            note=body.note,
        )
    )
    audit(db, c, p.id, "report.approved", snapshot=r["snapshot_hash"][:12], note=body.note)
    db.commit()
    return {"ok": True}


@app.get("/api/prospects/{pid}/audit")
def audit_log(pid: int, db: DB, c: C) -> list[dict]:
    p = get_prospect(db, c, pid)
    rows = db.scalars(
        select(AuditEvent)
        .where(AuditEvent.prospect_id == p.id, AuditEvent.tenant_id == c.tenant)
        .order_by(AuditEvent.id.desc())
        .limit(300)
    )
    return [{"at": a.at, "user": a.user, "action": a.action, "detail": a.detail} for a in rows]


@app.get("/api/prospects/{pid}/report.pdf")
def report_pdf(pid: int, db: DB, c: C, lang: Literal["en", "it"] = "en") -> Response:
    from .report import render_client_report

    p = get_prospect(db, c, pid)
    r = client_safe(
        compute(db, c, p)
    )  # defence in depth: the client report never receives internal economics
    pdf = render_client_report(r, lang)
    safe_code = re.sub(r"[^A-Za-z0-9_-]", "", p.code)  # the code is user input; keep the header clean
    audit(
        db,
        c,
        p.id,
        "report.downloaded",
        snapshot=r["snapshot_hash"][:12],
        approved=bool(r["approval"] and r["approval"]["valid"]),
    )
    db.commit()
    return Response(
        pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="cost-review-{safe_code}-{lang}.pdf"'},
    )
