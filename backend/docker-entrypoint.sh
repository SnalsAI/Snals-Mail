#!/bin/bash
set -e

echo "🚀 SNALS Email Agent - Backend Startup"

# Aspetta che PostgreSQL sia pronto
echo "⏳ Aspetto PostgreSQL..."
until python << END
import sys
import psycopg2
try:
    conn = psycopg2.connect(
        dbname="${DATABASE_URL##*/}",
        user="${DATABASE_URL#*://}",
        host="postgres",
        password="${POSTGRES_PASSWORD:-snals_password}"
    )
except psycopg2.OperationalError:
    sys.exit(-1)
sys.exit(0)
END
do
  echo "PostgreSQL non ancora pronto - attendo..."
  sleep 2
done

echo "✅ PostgreSQL pronto!"

# Esegui migrations
echo "🔄 Esecuzione migrations database..."
alembic upgrade head

echo "✅ Database aggiornato!"

# Esegui comando
echo "▶️  Avvio applicazione..."
exec "$@"
