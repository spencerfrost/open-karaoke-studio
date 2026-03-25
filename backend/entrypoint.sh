#!/bin/bash
set -e

# Wait for Postgres to be ready
echo "Waiting for postgres..."
while ! pg_isready -h postgres -p 5432 -U ${POSTGRES_USER:-karaoke_user} > /dev/null 2> /dev/null; do
  sleep 1
done

echo "PostgreSQL started"

# Run alembic migrations
echo "Running database migrations..."
alembic upgrade head

echo "Migrations complete"

# Start the application
exec "$@"
