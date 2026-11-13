"""Parallel OCR reads the same pages as sequential reading; its pool follows the real CPU quota (SC-5.11)."""

from __future__ import annotations

import io
import shutil
from pathlib import Path

import pypdfium2
import pytest

from pce.demo import generate
from pce.extraction import layout


def _snapshot(pages: list[layout.PageInfo]) -> list:
    return [
        (
            p.number,
            p.width,
            p.height,
            p.engine,
            [(ln.engine, ln.confidence, [(c.text, c.bbox) for c in ln.cells]) for ln in p.lines],
        )
        for p in pages
    ]


@pytest.fixture(scope="module")
def synthetic_scan(tmp_path_factory: pytest.TempPathFactory) -> bytes:
    """A 4-page image-only PDF rasterised from the SYNTHETIC demo documents."""
    out = tmp_path_factory.mktemp("demo")
    images = []
    for path in sorted(p for p in generate.generate(out) if p.suffix == ".pdf" and "scan" not in p.name)[:4]:
        pdf = pypdfium2.PdfDocument(str(path))
        images.append(pdf[0].render(scale=200 / 72).to_pil().convert("L"))
        pdf.close()
    buf = io.BytesIO()
    images[0].save(buf, "PDF", resolution=200.0, save_all=True, append_images=images[1:])
    return buf.getvalue()


@pytest.mark.ocr
@pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract binary not installed")
def test_parallel_ocr_matches_sequential(synthetic_scan: bytes, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PCE_OCR_WORKERS", "1")
    sequential = layout.read_pdf(synthetic_scan)
    monkeypatch.setenv("PCE_OCR_WORKERS", "4")
    parallel = layout.read_pdf(synthetic_scan)
    assert [p.engine for p in parallel] == [layout.ocr_engine()] * 4
    assert _snapshot(parallel) == _snapshot(sequential)


@pytest.mark.parametrize(
    ("env", "cpu_max", "affinity", "expected"),
    [
        ("3", None, 8, 3),  # operator override wins
        ("0", None, 8, 1),  # never below one
        (None, "15000 100000", 8, 1),  # Render free: 0.15 CPU
        (None, "250000 100000", 8, 2),  # 2.5 CPUs
        (None, "max 100000", 2, 2),  # no quota: CPUs we may run on
        (None, None, 16, 4),  # capped: Tesseract per page is memory-heavy
    ],
)
def test_ocr_workers(
    env: str | None,
    cpu_max: str | None,
    affinity: int,
    expected: int,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if env is None:
        monkeypatch.delenv("PCE_OCR_WORKERS", raising=False)
    else:
        monkeypatch.setenv("PCE_OCR_WORKERS", env)
    quota = tmp_path / "cpu.max"
    if cpu_max is not None:
        quota.write_text(cpu_max + "\n")
    monkeypatch.setattr(layout, "CGROUP_CPU_MAX", quota)
    monkeypatch.setattr(layout.os, "sched_getaffinity", lambda _pid: set(range(affinity)))
    assert layout.ocr_workers() == expected


def test_upload_route_runs_off_the_event_loop() -> None:
    """Reading a scan takes seconds to minutes; an ``async def`` route would freeze every other request."""
    import inspect

    from pce import api

    assert not inspect.iscoroutinefunction(api.upload)
