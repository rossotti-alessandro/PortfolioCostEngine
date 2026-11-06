"""Real public documents (price lists, KIDs) used as an extraction test corpus.

The files are third-party copyright, so they are never committed: ``data/reference/public_corpus.csv``
lists URL + SHA-256 + the values a human read on the page, and this module downloads them into
``var/public_corpus`` (git-ignored) and verifies each hash. Only public URLs are fetched; nothing
about any client is sent. Run: ``python -m pce.demo.public_corpus [--check]``.
"""

from __future__ import annotations

import csv
import hashlib
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
MANIFEST = ROOT / "data" / "reference" / "public_corpus.csv"
TARGET = ROOT / "var" / "public_corpus"
USER_AGENT = "FeeLens-corpus-fetch/0.1 (public documents only)"


def entries() -> list[dict[str, str]]:
    with MANIFEST.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def expected(entry: dict[str, str]) -> dict[str, str]:
    """'a=1; b=2' -> {'a': '1', 'b': '2'}"""
    out = {}
    for part in entry.get("expected", "").split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def fetch(check_only: bool = False) -> list[tuple[str, str]]:
    """Download missing files and verify hashes. Returns (file, status) pairs."""
    TARGET.mkdir(parents=True, exist_ok=True)
    report = []
    for e in entries():
        path = TARGET / e["file"]
        if not path.exists() and not check_only:
            if not e["url"].startswith("https://"):
                raise ValueError(f"manifest URL must be https: {e['file']}")
            req = urllib.request.Request(e["url"], headers={"User-Agent": USER_AGENT})  # noqa: S310
            with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310 - https checked above
                path.write_bytes(r.read())
        if not path.exists():
            report.append((e["file"], "missing"))
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        report.append((e["file"], "ok" if digest == e["sha256"] else f"hash changed ({digest[:12]})"))
    return report


if __name__ == "__main__":
    for name, status in fetch(check_only="--check" in sys.argv):
        print(f"{status:>20}  {name}")
