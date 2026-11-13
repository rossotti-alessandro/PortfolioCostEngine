"""Read several uploaded documents at the same time (SC-5.20).

``extract`` has the signature of ``parsers.extract`` and returns the same result. With more than one
worker it runs in a pool of processes: born-digital reading (pdfplumber, finder, verify) is pure Python,
so threads would take turns on the GIL, and pdfium is not thread safe. Every worker shares one
Tesseract limit (``layout.ocr_slots``), so several scans at once never start more OCR processes than
cores, while a lone long scan still OCRs its pages on all of them (SC-5.11).

Workers: ``PCE_DOC_WORKERS``, else the CPU quota (``layout.ocr_workers``). One worker (Render free plan)
runs inline: no extra process, no extra memory.
"""

from __future__ import annotations

import multiprocessing
import os
import threading
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures.process import BrokenProcessPool

from . import layout
from .models import ExtractionResult
from .parsers import extract as _extract

_POOL: ProcessPoolExecutor | None = None
_POOL_LOCK = threading.Lock()


def doc_workers() -> int:
    env = os.environ.get("PCE_DOC_WORKERS")
    return max(1, int(env)) if env else layout.ocr_workers()


def _init_worker(slots: object) -> None:
    layout.use_ocr_slots(slots)  # type: ignore[arg-type]


def _pool() -> ProcessPoolExecutor:
    global _POOL
    with _POOL_LOCK:
        if _POOL is None:
            # spawn, not fork: the API process runs threads, and forking a threaded process can deadlock
            ctx = multiprocessing.get_context("spawn")
            n = doc_workers()
            slots = ctx.BoundedSemaphore(layout.ocr_workers())
            _POOL = ProcessPoolExecutor(n, mp_context=ctx, initializer=_init_worker, initargs=(slots,))
        return _POOL


def extract(filename: str, data: bytes) -> tuple[ExtractionResult, list[layout.PageInfo]]:
    if doc_workers() <= 1:
        return _extract(filename, data)
    global _POOL
    try:
        return _pool().submit(_extract, filename, data).result()
    except BrokenProcessPool:  # a worker died (out of memory, killed): start a fresh pool, retry once
        with _POOL_LOCK:
            _POOL = None
        return _pool().submit(_extract, filename, data).result()
