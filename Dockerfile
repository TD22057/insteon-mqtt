ARG BUILD_FROM=ghcr.io/home-assistant/base-python:3.13-alpine3.24-2026.10.1
FROM $BUILD_FROM

ENV LANG C.UTF-8

COPY . /opt/insteon-mqtt

RUN pip3 install --no-cache-dir /opt/insteon-mqtt && \
    chmod +x /opt/insteon-mqtt/hassio/entrypoint.sh

CMD ["/opt/insteon-mqtt/hassio/entrypoint.sh"]
