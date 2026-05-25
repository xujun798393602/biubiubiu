# Worker Agent Dockerfile
# Supports both Playwright UI tests and Locust performance tests

FROM python:3.11-slim

# Use Chinese mirrors for faster downloads
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list 2>/dev/null || true

# Install only essential tools; Playwright deps are handled by `playwright install --with-deps`
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    tini \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies with Chinese mirror
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com -r requirements.txt

# Install Playwright browsers (with-deps handles all Chromium system deps)
RUN playwright install --with-deps chromium

# Copy agent code
COPY agent/ ./agent/

# Create non-root user for security
RUN useradd -m -u 1000 worker && \
    chown -R worker:worker /app
USER worker

# Environment variables with defaults
ENV BACKEND_URL=http://backend:8000
ENV REDIS_URL=redis://redis:6379/0
ENV NODE_TYPE=MIXED
ENV NODE_NAME=""
ENV API_KEY=""
ENV MAX_CONCURRENT=5
ENV HEARTBEAT_INTERVAL=10
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import redis; r = redis.from_url('${REDIS_URL}'); r.ping()" || exit 1

# Run the agent
CMD ["python", "-m", "agent"]
