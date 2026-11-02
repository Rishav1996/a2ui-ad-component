# ==============================================================================
# Production Dockerfile for A2UI v0.9 Server & Google ADK Multi-Agent Engine
# Optimized for Standalone Container Runtimes (Cloud Run, Docker, K8s)
# ==============================================================================
FROM python:3.12-slim

# Set environment variables for Python in container
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    HOST=0.0.0.0

WORKDIR /app

# Install system dependencies (curl for healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager for fast, deterministic installs
RUN pip install --no-cache-dir uv

# Copy dependency specifications first for layer caching
COPY pyproject.toml ./

# Install project dependencies
RUN uv pip install --system --no-cache-dir -e .

# Copy application code
COPY . .

# Expose server port (Cloud Run defaults to 8080)
EXPOSE 8080

# Health check probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT}/api/analytics || exit 1

# Launch FastAPI ASGI server
CMD ["python", "run_adk_server.py"]

