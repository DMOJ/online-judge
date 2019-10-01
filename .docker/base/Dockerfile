FROM debian:buster

# Change to pymysql if using gevent
RUN apt-get update && \
    apt-get install -y curl git python3-pip libmariadb-dev && \
    curl -sL https://deb.nodesource.com/setup_12.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    npm install -g sass postcss-cli autoprefixer && \
    pip3 install --upgrade pip mysqlclient uwsgi && \
    mkdir -p /code /code/static && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt /code
WORKDIR /code
ENV PYTHONUNBUFFERED 1
RUN pip3 install -r requirements.txt

COPY . /code
COPY .docker/local_settings.py /code/dmoj/
