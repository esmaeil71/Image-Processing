#!/bin/sh
set -e
cd /app
# POSIX sh (dash) — not bash — so use prefix strip, not ${VAR/pattern/rep}
case "$DATABASE_URL" in
  postgresql+asyncpg://*)
    export ALEMBIC_DATABASE_URL="postgresql://${DATABASE_URL#postgresql+asyncpg://}"
    ;;
  *)
    export ALEMBIC_DATABASE_URL="$DATABASE_URL"
    ;;
esac
alembic upgrade head
# Admin must be created — do not swallow errors (was causing "Invalid credentials" with no user)
python -m app.seed
python /app/scripts/seed_models.py || true
exec "$@"
