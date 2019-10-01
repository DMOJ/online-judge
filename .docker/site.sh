#!/bin/bash
/code/.docker/boot.sh
exec uwsgi --ini /code/.docker/uwsgi.ini "$@"
