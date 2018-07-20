ARG BUILD_FROM
FROM $BUILD_FROM

ENV LANG C.UTF-8
RUN apk --no-cache add python3-dev

COPY . /opt/insteon-mqtt

RUN pip3 install /opt/insteon-mqtt && \
    chmod +x /opt/insteon-mqtt/hassio/entrypoint.sh

CMD ["/opt/insteon-mqtt/hassio/entrypoint.sh"]
