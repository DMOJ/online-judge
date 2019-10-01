FROM nginx:stable-alpine

RUN mkdir /code
COPY .docker/nginx/nginx.conf /etc/nginx/nginx.conf
COPY robots.txt 502.html logo.png /code/
COPY resources/icons/* /code/
COPY --from=dmoj-site-static:latest /code/static/* /code/
