#!/bin/sh
set -e
# Only the API container migrates/seeds (RUN_MIGRATIONS=true). The worker just starts.
if [ "$RUN_MIGRATIONS" = "true" ]; then
  alembic upgrade head
  if [ "$RUN_SEED" = "true" ]; then python -m app.seed; fi
fi
exec "$@"
