"""Re-download the public specimen corpus listed in data/reference/specimen_corpus.csv.

The PDFs are third-party copyrighted documents, so git holds only this manifest:
source URL, SHA-256, retrieval date and classification. This script fetches each
file into a git-ignored folder (default ``var/specimens``) and verifies the hash.

Usage (from the repo root, any Python 3.10+, no dependencies):
    python3 data/specimens/tools/fetch.py            # download missing files, verify all
    python3 data/specimens/tools/fetch.py --check    # verify local files only, no network

Publishers update documents in place (KIDs monthly, price lists yearly). A hash
mismatch therefore usually means "a newer version is online", not corruption: the
file is kept as ``<name>.new.pdf`` and reported, so a human can refresh the row.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "data" / "reference" / "specimen_corpus.csv"
USER_AGENT = "FeeLens-corpus-builder/0.1 (research; respects robots.txt)"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def download(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=90) as resp:  # noqa: S310 - URLs come from the reviewed manifest
        data = resp.read()
    if not data.startswith(b"%PDF"):
        raise ValueError("response is not a PDF")
    dest.write_bytes(data)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="verify local files only")
    ap.add_argument("--dest", type=Path, default=ROOT / "var" / "specimens")
    ap.add_argument("--manifest", type=Path, default=MANIFEST)
    args = ap.parse_args()
    args.dest.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(args.manifest.open(encoding="utf-8")))
    counts = {"ok": 0, "changed": 0, "missing": 0, "failed": 0}
    for row in rows:
        path = args.dest / row["file"]
        if not path.exists() and not args.check:
            try:
                download(row["url"], path)
                time.sleep(1)  # be polite to publishers
            except Exception as exc:  # noqa: BLE001 - report and continue with the next file
                print(f"FAILED   {row['file']}: {exc}")
                counts["failed"] += 1
                continue
        if not path.exists():
            print(f"MISSING  {row['file']}")
            counts["missing"] += 1
            continue
        if sha256(path) == row["sha256"]:
            counts["ok"] += 1
            continue
        changed = path.with_suffix(".new.pdf")
        path.replace(changed)
        print(f"CHANGED  {row['file']}: publisher's copy differs from the manifest hash, kept as {changed.name}")
        counts["changed"] += 1
    print(f"{len(rows)} rows: " + ", ".join(f"{k} {v}" for k, v in counts.items()))
    return 0 if counts["ok"] == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
