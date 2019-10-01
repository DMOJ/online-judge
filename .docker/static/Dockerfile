FROM dmoj-site-base:latest

ENV SECRET_KEY invalid
ENV SQL_DATABASE_NAME invalid
ENV SQL_DATABASE_USER invalid
ENV SQL_DATABASE_PASSWORD invalid

RUN ./make_style.sh
RUN mkdir -p /log && \
    echo yes | python3 manage.py collectstatic && \
    python3 manage.py compilejsi18n
