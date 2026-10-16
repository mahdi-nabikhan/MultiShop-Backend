#!/bin/sh
set -e

cd /app/backend

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec gunicorn Multi_Shop.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 2 \
    --timeout 60