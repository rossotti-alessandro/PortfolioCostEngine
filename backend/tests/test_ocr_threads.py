"""Tesseract runs single-threaded unless the operator says otherwise (SC-5.9).

Tesseract's OpenMP threads busy-wait: on a CPU shared with other work one page took 87 s instead of 2 s.
pytesseract starts Tesseract as a subprocess, so the setting must be in the inherited environment.
"""

import os
import subprocess
import sys


def _limit_after_import(env: dict[str, str]) -> str:
    code = "import os, pce.extraction; print(os.environ.get('OMP_THREAD_LIMIT', ''))"
    return subprocess.run(
        [sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True
    ).stdout.strip()


def test_import_sets_single_thread_ocr() -> None:
    env = {k: v for k, v in os.environ.items() if k != "OMP_THREAD_LIMIT"}
    assert _limit_after_import(env) == "1"


def test_explicit_limit_is_kept() -> None:
    assert _limit_after_import({**os.environ, "OMP_THREAD_LIMIT": "4"}) == "4"
