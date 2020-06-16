FROM python:slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        texlive-binaries texlive-generic-extra texlive-generic-recommended \
        texlive-latex-base texlive-latex-extra texlive-latex-recommended \
        texlive-pictures texlive-pstricks librsvg2-bin xxd imagemagick git \
        build-essential python-dev

RUN git clone https://github.com/DMOJ/texoid/
WORKDIR /texoid/
RUN pip3 install -e .

EXPOSE 8888
ENTRYPOINT texoid --address=texoid --port=8888
