#!/usr/bin/env sh
# Phase 0 — idempotent local bootstrap (migrate + celery beat schedules).
set -e
cd "$(dirname "$0")/.."

PYTHON="${PYTHON:-.venv/bin/python}"
if [ ! -x "$PYTHON" ]; then
  PYTHON=python3
fi

if [ ! -f .env ]; then
  echo "No .env found — copy .env.example to .env and adjust CORS_ALLOWED_ORIGINS for your web app."
  exit 1
fi

echo "==> migrate"
"$PYTHON" manage.py migrate --noinput

echo "==> seed_celery_beat"
"$PYTHON" manage.py seed_celery_beat

echo "==> seed_catalog"
"$PYTHON" manage.py seed_catalog

echo "==> done"
echo "    Run server:  $PYTHON manage.py runserver"
echo "    Or ASGI:     $PYTHON -m daphne -b 0.0.0.0 -p 8000 core.asgi:application"
echo "    Swagger:     http://127.0.0.1:8000/api/schema/swagger-ui/"
echo "    Optional:    $PYTHON manage.py seed_demo_auctions  # demo seller + auctions"
