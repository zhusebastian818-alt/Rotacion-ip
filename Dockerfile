# ==============================================================================
# Multi-Stage Secure Dockerfile for B2B Traffic Fine Monitoring SaaS
# Hardened according to CIS Docker Benchmark & Cybersecurity Best Practices
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Build Dependencies
# ------------------------------------------------------------------------------
FROM python:3.12-slim@sha256:7bc52cf126284646700de0c4cd2e847cdccfd8b209d297a7e8e788bc535e982d AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies if needed, upgrade pip
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt

# ------------------------------------------------------------------------------
# Stage 2: Hardened Runtime Environment
# ------------------------------------------------------------------------------
FROM python:3.12-slim@sha256:7bc52cf126284646700de0c4cd2e847cdccfd8b209d297a7e8e788bc535e982d AS runtime

# Secure runtime environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PATH="/install/bin:$PATH" \
    PYTHONPATH="/app:$PYTHONPATH"

# Install minimal runtime libraries and curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Cybersecurity requirement: Create non-root system user and group (UID/GID 10001)
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /sbin/nologin -M -d /nonexistent appuser

WORKDIR /app

# Copy installed Python packages from builder stage
COPY --from=builder /install /usr/local

# Copy application source code with restricted permissions
COPY --chown=appuser:appgroup app /app/app
COPY --chown=appuser:appgroup main.py /app/main.py
COPY --chown=appuser:appgroup requirements.txt /app/requirements.txt

# Enforce least privilege: drop root privileges
USER 10001:10001

# Document exposed unprivileged port
EXPOSE 8000

# Container healthcheck probe without exposing internal services
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Launch application via uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--no-server-header"]
