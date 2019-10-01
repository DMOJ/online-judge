#!/bin/bash

cd /code
python3 manage.py compilemessages

# TODO: only if nothing in db, or provide a command
# to do this that people run the first time
python3 manage.py migrate
python3 manage.py check
python3 manage.py loaddata navbar
python3 manage.py loaddata language_small
