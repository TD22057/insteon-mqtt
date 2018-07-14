ARG BUILD_FROM
FROM $BUILD_FROM

ENV LANG C.UTF-8
RUN apk --no-cache add python3-dev

COPY . /opt/insteon-mqtt

RUN pip3 install /opt/insteon-mqtt

CMD ["entrypoint.sh"]
