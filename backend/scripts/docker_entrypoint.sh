#!/bin/sh
set -e
cd /app
export ALEMBIC_DATABASE_URL="${DATABASE_URL/postgresql+asyncpg:\/\//postgresql://}"
alembic upgrade head
python -m app.seed || true
python /app/scripts/seed_models.py || true
exec "$@"
