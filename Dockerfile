# syntax=docker/dockerfile:1.4

# --- Base Image ---
FROM python:3.11-slim as base
WORKDIR /app
RUN useradd --create-home --shell /bin/bash appuser

# --- Build Stage ---
FROM base as builder
RUN apt-get update && apt-get install -y --no-install-recommends build-essential git
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt
COPY . .
RUN chown -R appuser:appuser /app

# --- Final Stage ---
FROM base as final
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /app /app
RUN mkdir -p /app/output /app/cache /app/logs /app/cores && \
    chown -R appuser:appuser /app
USER appuser
EXPOSE 8080 9090
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8080/healthz || exit 1
ENTRYPOINT ["python", "-m", "src.main"]
