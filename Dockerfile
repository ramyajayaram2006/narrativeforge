# ── Stage 1: build deps ───────────────────────────────────────────────────────
FROM python:3.11-slim AS builder
WORKDIR /install
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/deps -r requirements.txt

# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# System deps for psycopg2-binary
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

WORKDIR /app
COPY --from=builder /deps /usr/local
COPY app.py auth.py dashboard.py database.py workspace.py \
     styles.py utils.py relationship_map.py logger.py \
     autosave.py language_support.py collaboration.py ./

# Data volume mount point (SQLite db or just config)
RUN mkdir -p /data && chown appuser:appgroup /data

USER appuser

ENV STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    STREAMLIT_SERVER_HEADLESS=true \
    NARRATIVEFORGE_DB=/data/narrativeforge.db \
    NARRATIVEFORGE_MODEL=llama3.2 \
    OLLAMA_HOST=http://ollama:11434

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
  CMD curl -f http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "app.py", \
            "--server.port=8501", "--server.address=0.0.0.0"]
