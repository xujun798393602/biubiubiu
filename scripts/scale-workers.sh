#!/bin/bash
# Quick scale worker nodes script
# Usage: ./scripts/scale-workers.sh [playwright_count] [locust_count] [mixed_count]

set -e

PLAYWRIGHT_COUNT=${1:-1}
LOCUST_COUNT=${2:-1}
MIXED_COUNT=${3:-0}

echo "=== Worker Node Scaling ==="
echo "Playwright workers: $PLAYWRIGHT_COUNT"
echo "Locust workers: $LOCUST_COUNT"
echo "Mixed workers: $MIXED_COUNT"
echo ""

# Scale Playwright workers
if [ "$PLAYWRIGHT_COUNT" -gt 0 ]; then
    echo "Scaling Playwright workers to $PLAYWRIGHT_COUNT..."
    for i in $(seq 1 $PLAYWRIGHT_COUNT); do
        WORKER_INDEX=$i docker compose -f docker-compose.yml -f docker-compose.scale.yml \
            up -d worker-playwright
    done
fi

# Scale Locust workers
if [ "$LOCUST_COUNT" -gt 0 ]; then
    echo "Scaling Locust workers to $LOCUST_COUNT..."
    for i in $(seq 1 $LOCUST_COUNT); do
        WORKER_INDEX=$i docker compose -f docker-compose.yml -f docker-compose.scale.yml \
            up -d worker-locust
    done
fi

# Scale Mixed workers
if [ "$MIXED_COUNT" -gt 0 ]; then
    echo "Scaling Mixed workers to $MIXED_COUNT..."
    for i in $(seq 1 $MIXED_COUNT); do
        WORKER_INDEX=$i docker compose -f docker-compose.yml -f docker-compose.scale.yml \
            up -d worker-mixed
    done
fi

echo ""
echo "=== Current Worker Status ==="
docker compose ps worker-* 2>/dev/null || echo "No workers running"

echo ""
echo "=== Worker Logs ==="
echo "View logs: docker compose logs -f worker-playwright worker-locust worker-mixed"
echo "Stop all: docker compose -f docker-compose.yml -f docker-compose.scale.yml down"
