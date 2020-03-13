#!/bin/bash

set -o errexit
set -o nounset


readonly GUNICORN='/venv/bin/gunicorn'
readonly GUNICORN_WORKERS=${GUNICORN_WORKERS:-4}

readonly BIND_HOST='0.0.0.0'
readonly BIND_PORT=8000
readonly APP_MODULE='pulpcore.app.wsgi:application'


exec "${GUNICORN}" \
  --bind "${BIND_HOST}:${BIND_PORT}" \
  --workers "${GUNICORN_WORKERS}" \
  --access-logfile - \
  --reload \
  "${APP_MODULE}"
