# FeeLens demo: one container, API + built UI on port 8000. SYNTHETIC data only on any public deployment.
FROM node:22-slim AS ui
WORKDIR /app/frontend
RUN corepack enable
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm exec vite build

FROM python:3.12-slim
# Tesseract (eng/ita/deu/fra) for scanned statements; ocrmypdf is called as a CLI, never imported.
RUN apt-get update && apt-get install -y --no-install-recommends \
      tesseract-ocr tesseract-ocr-eng tesseract-ocr-ita tesseract-ocr-deu tesseract-ocr-fra \
      ghostscript qpdf libmagic1 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.9.5 /uv /usr/local/bin/uv
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock backend/README.md backend/
RUN cd backend && uv sync --frozen --no-dev --no-install-project
COPY backend/ backend/
COPY data/ data/
RUN cd backend && uv sync --frozen --no-dev
COPY --from=ui /app/frontend/dist frontend/dist
# OMP_THREAD_LIMIT=1: Tesseract threads thrash on small shared CPUs (free tiers).
ENV PCE_DATA_DIR=/app/var PCE_ALLOW_EXTERNAL_AI=false PORT=8000 OMP_THREAD_LIMIT=1
EXPOSE 8000
# --proxy-headers: behind Render's proxy the client address (login throttling) comes from X-Forwarded-For.
CMD ["sh", "-c", "cd backend && exec .venv/bin/uvicorn pce.serve:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips '*' --no-server-header"]
