#!/bin/bash
# Run database migrations
# Usage: ./scripts/run-migration.sh

set -e

echo "=== Running Database Migrations ==="

# Run migration using docker compose
docker compose exec backend alembic upgrade head

echo "=== Migration Complete ==="
