FROM node:8-stretch-slim

RUN apt-get update && \
    apt-get install -y librsvg2-dev git make g++

RUN git clone https://github.com/wikimedia/mathoid
WORKDIR /mathoid
RUN npm install

EXPOSE 10044

CMD ["/mathoid/server.js"]
