#!/usr/bin/env bash

set -eux

cd /opt/wlmoj

runuser -u dmoj /opt/venv/bin/python3 -- manage.py migrate

if [[ $WLMOJ_MODE == *"demo"* ]]; then
  runuser -u dmoj /opt/venv/bin/python3 -- manage.py loaddata navbar
  runuser -u dmoj /opt/venv/bin/python3 -- manage.py loaddata language_small
  runuser -u dmoj /opt/venv/bin/python3 -- manage.py loaddata demo
fi

if [[ $WLMOJ_MODE == *"celery"* ]]; then
  # TODO: run not as root
  runuser -u dmoj /opt/venv/bin/celery -- -A dmoj_celery worker &
fi
if [[ $WLMOJ_MODE == *"bridged"* ]]; then
  runuser -u dmoj /opt/venv/bin/python3 -- manage.py runbridged &
fi
if [[ $WLMOJ_MODE == *"evsv"* ]]; then
  runuser -u dmoj /opt/wlmoj-evsv/run.sh &
fi
if [[ $WLMOJ_MODE == *"uwsgi"* ]]; then
  /opt/venv/bin/uwsgi --ini /opt/wlmoj-etc/uwsgi.ini &
fi

wait
