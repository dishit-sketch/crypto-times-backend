#!/usr/bin/env bash
set -o errexit
echo "Running migrations..."
python manage.py migrate
echo "Migrations done. Starting server..."
gunicorn crypto_times.wsgi:application --bind 0.0.0.0:$PORT --workers 3