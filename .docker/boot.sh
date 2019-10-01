#!/bin/bash

cd /code

echo yes | python3 manage.py collectstatic
python3 manage.py compilemessages
python3 manage.py compilejsi18n

# TODO: only if nothing in db, or provide a command
# to do this that people run the first time
python3 manage.py migrate
python3 manage.py check
python3 manage.py loaddata navbar
python3 manage.py loaddata language_small
