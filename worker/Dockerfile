# Worker Agent Dockerfile
# Supports both Playwright UI tests and Locust performance tests

FROM python:3.11-slim

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libdbus-1-3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libatspi2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
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
