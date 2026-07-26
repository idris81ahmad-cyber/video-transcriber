# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Video Transcriber — production image (CPU)
# ---------------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System deps: ffmpeg is required for video/audio handling
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

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Non-root user
RUN useradd --create-home --shell /bin/bash appuser
USER appuser
WORKDIR /home/appuser

# Default entrypoint
ENTRYPOINT ["video-transcriber"]
CMD ["--help"]

# Optional for web UI
EXPOSE 7860

# Healthcheck (optional — useful when running web mode)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD video-transcriber --version || exit 1
