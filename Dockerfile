# syntax=docker/dockerfile:1.4

# --- Build Stage ---
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends build-essential git

# Create a non-root user for the build
RUN useradd --create-home --shell /bin/bash appuser

# Copy requirements and install dependencies
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# --- Final Stage ---
FROM python:3.11-slim as final

WORKDIR /app

# Create a non-root user for the runtime
RUN useradd --create-home --shell /bin/bash appuser

# Copy installed dependencies from the builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copy the application from the builder stage
COPY --from=builder /app /app

# Create and set ownership for necessary directories
RUN mkdir -p /app/output /app/cache /app/logs /app/cores && \
    chown -R appuser:appuser /app

# Set the non-root user
USER appuser

# Expose ports
EXPOSE 8080 9090

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8080/healthz || exit 1

# Entrypoint
ENTRYPOINT ["python", "-m", "src.main"]
