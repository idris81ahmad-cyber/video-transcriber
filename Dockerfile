# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Video Transcriber — production image (CPU)
# ---------------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/home/appuser/.cache/huggingface \
    XDG_CACHE_HOME=/home/appuser/.cache

RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ---------------------------------------------------------------------------
FROM base AS builder

COPY pyproject.toml README.md LICENSE ./ 
COPY src ./src

RUN pip install --upgrade pip \
    && pip install ".[url,web]"

# ---------------------------------------------------------------------------
FROM base AS runtime

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

RUN useradd --create-home --shell /bin/bash appuser \
    && mkdir -p /home/appuser/.cache/huggingface /data /output \
    && chown -R appuser:appuser /home/appuser /data /output

USER appuser
WORKDIR /data

ENTRYPOINT ["video-transcriber"]
CMD ["--help"]

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD video-transcriber --version || exit 1
