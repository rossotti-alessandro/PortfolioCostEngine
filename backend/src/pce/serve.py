"""Single-process deployment: the API plus the built frontend (frontend/dist) on one port.

Used by the Dockerfile (``uvicorn pce.serve:app``). Development keeps Vite on :5173 with its /api proxy.
Unknown non-API paths return index.html so client-side routes (/p/1/costs) survive a page reload.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse

from .api import app

DIST = Path(
    os.environ.get("PCE_STATIC_DIR", Path(__file__).resolve().parents[3] / "frontend" / "dist")
).resolve()


@app.get("/{path:path}", include_in_schema=False)
def spa(path: str) -> FileResponse:
    if path.startswith("api/"):
        raise HTTPException(404)
    f = (DIST / path).resolve()
    if path and f.is_file() and f.is_relative_to(DIST):  # no ../ escapes
        return FileResponse(f)
    return FileResponse(DIST / "index.html")
