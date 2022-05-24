FROM wlmoj_judge:latest

COPY ./problems-init /opt/wlmoj_judge/problems-init
COPY ./config.yml /opt/wlmoj_judge/config.yml
COPY ./run.sh /opt/wlmoj_judge/run.sh

RUN (echo; cat /judge-runtime-paths.yml) >> /opt/wlmoj_judge/config.yml

CMD ["/opt/wlmoj_judge/run.sh"]
ENTRYPOINT []
