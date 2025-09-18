# syntax=docker/dockerfile:1.4
################################################################################
# Multi-stage Dockerfile - V2Ray/Xray scanner (Python + optional Go + optional cores)
# - safe defaults, conditional stages, non-root runtime, healthcheck
# - build args allow controlling XRAY/HIDDIFY versions or use bundled tmp_setup zips
################################################################################

###############################################################################
# Stage: Python builder (virtualenv + optional wheels)
###############################################################################
ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim AS py-builder
ENV VENV_PATH=/opt/venv
WORKDIR /src

# Minimal build tools for possible wheel compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
      gcc \
      curl \
      unzip \
    && rm -rf /var/lib/apt/lists/*

# Copy project (copying whole repo; Docker layer caching will use later)
COPY . /src

# Create venv and install build tools
RUN python -m venv ${VENV_PATH} \
    && ${VENV_PATH}/bin/pip install --upgrade pip setuptools wheel build

# Install requirements if provided
RUN if [ -f requirements.txt ]; then ${VENV_PATH}/bin/pip install --no-cache-dir -r requirements.txt; fi

# Build wheel(s) if project has packaging metadata
RUN if [ -f pyproject.toml ] || [ -f setup.py ]; then \
      ${VENV_PATH}/bin/python -m build --wheel --outdir /src/dist || true; \
    fi

###############################################################################
# Stage: Go builder (optional, only if go.mod exists)
###############################################################################
ARG GO_VERSION=1.21
FROM golang:${GO_VERSION} AS go-builder
WORKDIR /src
COPY . /src

# If repo has go.mod, download deps and attempt builds (best-effort; won't fail whole build)
RUN if [ -f go.mod ]; then \
      go env -w GOPROXY="https://proxy.golang.org,direct" && go mod download || true; \
    fi && \
    mkdir -p /go-bin && \
    if [ -d ./cmd ]; then \
      for d in cmd/*; do \
        if [ -d "$d" ]; then \
          name=$(basename "$d"); \
          echo "Building cmd/${name} -> /go-bin/${name}"; \
          env CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -trimpath -ldflags "-s -w" -o /go-bin/${name} ./cmd/${name} || true; \
        fi; \
      done; \
    else \
      echo "No cmd/ folder; attempting top-level go build (best-effort)"; \
      env CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -trimpath -ldflags "-s -w" -o /go-bin/app ./... || true; \
    fi

###############################################################################
# Stage: cores extraction (optional zipped cores or fallback downloads)
###############################################################################
ARG PYTHON_VERSION=${PYTHON_VERSION}
ARG XRAY_VERSION=v1.8.10
ARG HIDDIFY_VERSION=v3.2.0
ARG XRAY_URL=https://github.com/XTLS/Xray-core/releases/download/${XRAY_VERSION}/Xray-linux-64.zip
ARG HIDDIFY_URL=https://github.com/hiddify/hiddify-core/releases/download/${HIDDIFY_VERSION}/hiddify-linux-amd64.zip

FROM python:${PYTHON_VERSION}-slim AS cores
WORKDIR /tmp/cores
RUN apt-get update && apt-get install -y --no-install-recommends curl unzip ca-certificates && rm -rf /var/lib/apt/lists/*

# Copy any bundled cores (if repo includes tmp_setup/xray.zip or tmp_setup/hiddify.zip)
COPY tmp_setup /tmp_setup

# Extract xray if present; otherwise try download (non-fatal)
RUN mkdir -p /tmp/extract_xray /usr/local/bin && \
    if [ -f /tmp_setup/xray.zip ]; then \
      echo "Using bundled tmp_setup/xray.zip"; unzip -q /tmp_setup/xray.zip -d /tmp/extract_xray || true; \
    else \
      echo "No bundled xray.zip; skipping download in build (to avoid network in some CI)" && true; \
    fi && \
    found=$(find /tmp/extract_xray -type f -perm /111 -print -quit || true) && \
    if [ -n "$found" ]; then cp "$found" /usr/local/bin/xray-core || true; fi || true

# Extract hiddify similarly
RUN mkdir -p /tmp/extract_hiddify && \
    if [ -f /tmp_setup/hiddify.zip ]; then \
      echo "Using bundled tmp_setup/hiddify.zip"; unzip -q /tmp_setup/hiddify.zip -d /tmp/extract_hiddify || true; \
    else \
      echo "No bundled hiddify.zip; skipping download in build" && true; \
    fi && \
    found2=$(find /tmp/extract_hiddify -type f -perm /111 -print -quit || true) && \
    if [ -n "$found2" ]; then cp "$found2" /usr/local/bin/hiddify-cli || true; fi || true

# Ensure executables are executable (if present)
RUN chmod +x /usr/local/bin/xray-core /usr/local/bin/hiddify-cli || true

###############################################################################
# Stage: Final runtime (minimal, non-root, runs Python scanner by default)
###############################################################################
FROM python:${PYTHON_VERSION}-slim AS runtime
LABEL org.opencontainers.image.title="Stealth Scanner" \
      org.opencontainers.image.description="Automated V2Ray/Xray scanner (Python-driven) - built from repo" \
      org.opencontainers.image.licenses="MIT"

WORKDIR /app

# Small runtime deps
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl unzip && rm -rf /var/lib/apt/lists/*

# Copy virtualenv from py-builder (if present)
COPY --from=py-builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}" PYTHONUNBUFFERED=1

# Copy Go binaries (if built)
COPY --from=go-builder /go-bin/ /usr/local/bin/ || true

# Copy optional cores (if extracted)
COPY --from=cores /usr/local/bin/xray-core /usr/local/bin/ 2>/dev/null || true
COPY --from=cores /usr/local/bin/hiddify-cli /usr/local/bin/ 2>/dev/null || true

# Copy repository files
COPY . /app

# Create non-root user and prepare folders
RUN groupadd -r scanner && useradd --no-log-init -r -g scanner -m -d /home/scanner scanner && \
    mkdir -p /app/output /app/cache /app/logs /app/cores && \
    chown -R scanner:scanner /app /app/output /app/cache /app/logs /app/cores

# Create robust entrypoint script (owned by root but will be executed as non-root below)
RUN cat > /usr/local/bin/entrypoint.sh <<'SH'
#!/bin/sh
set -eu

# default envs (can override at runtime)
: "${XRAY_BINARY:=/usr/local/bin/xray-core}"
: "${HIDDIFY_BINARY:=/usr/local/bin/hiddify-cli}"
: "${OUTPUT_DIR:=/app/output}"
: "${CACHE_DIR:=/app/cache}"
: "${LOGS_DIR:=/app/logs}"

# Ensure directories exist
mkdir -p "$OUTPUT_DIR" "$CACHE_DIR" "$LOGS_DIR" /app/cores

# Make binaries executable if present
if [ -f "$XRAY_BINARY" ]; then chmod +x "$XRAY_BINARY" || true; fi
if [ -f "$HIDDIFY_BINARY" ]; then chmod +x "$HIDDIFY_BINARY" || true; fi

# If any args provided, run them (useful for debug or alternative commands)
if [ "$#" -gt 0 ]; then
  exec "$@"
fi

# Prefer running the python module src.main if available
if python -c "import importlib, sys, pkgutil; sys.exit(0 if pkgutil.find_loader('src') else 1)" >/dev/null 2>&1; then
  exec python -u -m src.main
fi

# Fallback to direct script if present
if [ -f /app/src/main.py ]; then
  exec python -u /app/src/main.py
fi

echo "No runnable entrypoint found (python module src or src/main.py). Dropping to shell." >&2
exec /bin/sh
SH

RUN chmod +x /usr/local/bin/entrypoint.sh && chown scanner:scanner /usr/local/bin/entrypoint.sh

# Switch to non-root user
USER scanner
ENV HOME=/home/scanner

# Expose common ports (change as needed)
EXPOSE 8080 9090

# Healthcheck (adjust path if your app uses different health endpoint)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -fS http://127.0.0.1:8080/health || exit 1

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD []

################################################################################
# End of Dockerfile
################################################################################