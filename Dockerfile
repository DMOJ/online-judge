FROM debian:buster

RUN apt-get update && apt-get install -y curl git python3-pip
RUN curl -sL https://deb.nodesource.com/setup_12.x | bash -
RUN apt-get install -y nodejs
RUN npm install -g sass postcss-cli autoprefixer
RUN pip3 install --upgrade pip

RUN mkdir -p /code
COPY requirements.txt /code
WORKDIR /code
ENV PYTHONUNBUFFERED 1
RUN pip3 install -r requirements.txt



COPY . /code
COPY .docker/local_settings.py /code/dmoj/
RUN ls /code/dmoj

RUN git submodule init && git submodule update




RUN ./make_style.sh

# Change to pymysql if using gevent
RUN apt-get install -y libmariadb-dev
RUN pip3 install mysqlclient  


RUN mkdir /code/static

EXPOSE 8000
EXPOSE 9999
EXPOSE 9998
EXPOSE 15100
EXPOSE 15101
EXPOSE 15102
