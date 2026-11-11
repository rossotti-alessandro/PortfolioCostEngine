#!/usr/bin/env bash
# One-time machine setup: system OCR packages, Python env, git hooks.
# Usage: ./scripts/bootstrap.sh [--docling]
#   --docling   also install the Docling layout/table models (PyTorch, ~1-6 GB depending on platform)
# Supported: macOS (Homebrew) and Debian/Ubuntu (apt). Other systems: see docs/SETUP.md.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

if [ "$(uname)" = "Darwin" ]; then
  command -v brew >/dev/null || { echo "Install Homebrew first: https://brew.sh" >&2; exit 1; }
  brew install tesseract tesseract-lang ghostscript qpdf poppler libmagic pngquant uv node pnpm
elif command -v apt-get >/dev/null; then
  SUDO=""; [ "$(id -u)" = "0" ] || SUDO="sudo"
  $SUDO apt-get update -qq
  $SUDO env DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
    tesseract-ocr tesseract-ocr-eng tesseract-ocr-ita tesseract-ocr-deu tesseract-ocr-fra \
    ghostscript qpdf poppler-utils unpaper pngquant libmagic1
  command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
else
  echo "Unsupported OS: install the packages listed in docs/SETUP.md manually." >&2
fi

EXTRA=()
[ "${1:-}" = "--docling" ] && EXTRA=(--extra docling)
(cd backend && uv sync "${EXTRA[@]}")
(cd backend && uv run python -m pce.extraction.toolchain)
./scripts/setup-hooks.sh
echo "✓ bootstrap done"
