FROM debian:buster

RUN apt install -y git python3-pip
RUN git submodule init
RUN git submodule update


ENV PYTHONUNBUFFERED 1
RUN pip3 install --upgrade pip
RUN mkdir -p /code/site
WORKDIR /code/site
COPY requirements.txt /code/site
RUN pip3 install -r requirements.txt
COPY . /code/site
COPY .docker/local_settings.py /code/site/dmoj


RUN curl -sL https://deb.nodesource.com/setup_12.x | sudo -E bash -
RUN apt install -y nodejs
RUN npm install -g sass postcss-cli autoprefixer
RUN sh make_style.sh
RUN echo yes | python3 manage.py collectstatic
RUN python3 manage.py compilemessages
RUN python3 manage.py compilejsi18n


RUN python3 manage.py migrate


RUN python3 manage.py check
RUN python3 manage.py loaddata navbar
RUN python3 manage.py loaddata language_small


EXPOSE 8000
EXPOSE 9999
EXPOSE 9998
EXPOSE 15100
EXPOSE 15101
EXPOSE 15102
