FROM python:3.12-slim

WORKDIR /app

# System deps: build tools, display server, VNC, window manager, Chromium deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    xvfb fluxbox x11vnc \
    novnc websockify \
    supervisor \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libdrm2 libgbm1 libxkbcommon0 libatspi2.0-0 \
    libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
    libpango-1.0-0 libcairo2 libasound2t64 \
    libxcb1 libx11-6 libx11-xcb1 libxext6 libxshmfence1 \
    fonts-liberation fonts-noto-color-emoji fonts-unifont \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium browser (deps already installed above)
RUN playwright install chromium

COPY . .

RUN mkdir -p /var/log/backend /var/run

EXPOSE 8000 6080

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["supervisord", "-c", "/app/supervisord.conf"]
