#!/usr/bin/env bash
# Container entrypoint. The first argument selects the process role:
#   web          -> Gunicorn API server (default)
#   worker       -> Celery worker
#   beat         -> Celery beat scheduler
#   migrate      -> run migrations and exit
#   bootstrap    -> seed RBAC + demo data and exit
set -euo pipefail

ROLE="${1:-web}"

wait_for_db() {
  echo "Waiting for the database..."
  python <<'PY'
import os, time, sys
import psycopg
url = os.environ.get("DATABASE_URL", "")
for attempt in range(30):
    try:
        psycopg.connect(url, connect_timeout=3).close()
        print("Database is ready.")
        sys.exit(0)
    except Exception as exc:  # noqa: BLE001
        print(f"  db not ready ({attempt + 1}/30): {exc}")
        time.sleep(2)
sys.exit("Database did not become available in time.")
PY
}

case "$ROLE" in
  web)
    wait_for_db
    python manage.py migrate --noinput
    # Whitenoise's manifest storage refuses to start when staticfiles.json
    # exists but is partially written (interrupted previous collectstatic).
    # Wipe it so collectstatic always starts from a known state.
    rm -f /app/staticfiles/staticfiles.json
    python manage.py collectstatic --noinput
    exec gunicorn config.wsgi:application \
      --bind 0.0.0.0:8000 \
      --workers "${GUNICORN_WORKERS:-3}" \
      --timeout "${GUNICORN_TIMEOUT:-60}" \
      --access-logfile - --error-logfile -
    ;;
  worker)
    wait_for_db
    exec celery -A config worker -l "${CELERY_LOG_LEVEL:-info}"
    ;;
  beat)
    wait_for_db
    exec celery -A config beat -l "${CELERY_LOG_LEVEL:-info}" \
      --scheduler django_celery_beat.schedulers:DatabaseScheduler
    ;;
  migrate)
    wait_for_db
    exec python manage.py migrate --noinput
    ;;
  bootstrap)
    wait_for_db
    python manage.py migrate --noinput
    exec python manage.py bootstrap_demo
    ;;
  *)
    exec "$@"
    ;;
esac
