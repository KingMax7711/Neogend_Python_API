#!/usr/bin/env sh
set -e

echo "[start] Waiting for Postgres ${POSTGRES_HOST}:${POSTGRES_PORT}..."
until python - <<'PY'
import os, sys
import time
import psycopg2
host=os.getenv('POSTGRES_HOST','db')
port=int(os.getenv('POSTGRES_PORT','5432'))
user=os.getenv('POSTGRES_USER')
password=os.getenv('POSTGRES_PASSWORD')
dbname=os.getenv('POSTGRES_DB')
try:
    psycopg2.connect(host=host, port=port, user=user, password=password, dbname=dbname).close()
    sys.exit(0)
except Exception as e:
    print(e)
    sys.exit(1)
PY
do
  echo "Postgres not ready, retrying in 2s..."
  sleep 2
done

echo "[start] Running Alembic migrations..."
alembic upgrade head

echo "[start] Launching API..."
# Allow configuring which proxy IPs are trusted for X-Forwarded-* headers.
# Default to the current Nginx container IP if not provided.
# You can override this at runtime with FORWARDED_ALLOW_IPS (comma-separated list),
# e.g. "172.18.0.5,127.0.0.1" or "*" (trust all — not recommended).
FORWARDED_ALLOW_IPS=${FORWARDED_ALLOW_IPS:-172.18.0.5}
echo "[start] Using forwarded-allow-ips=$FORWARDED_ALLOW_IPS"

exec uvicorn main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --proxy-headers \
  --forwarded-allow-ips "$FORWARDED_ALLOW_IPS"
