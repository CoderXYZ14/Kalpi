#!/bin/sh
set -e

python manage.py migrate --noinput

if [ -n "$DJANGO_SUPERUSER_USERNAME" ]; then
  python manage.py createsuperuser --noinput 2>/dev/null || echo "User $DJANGO_SUPERUSER_USERNAME already exists"
fi

python manage.py recover_executions

exec gunicorn config.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 1 \
  --threads 4 \
  --timeout 120 \
  --access-logfile -
