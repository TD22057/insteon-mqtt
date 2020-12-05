#!/bin/sh

/bin/mkdir /config/insteon-mqtt/

/bin/cp /opt/insteon-mqtt/config.yaml /config/insteon-mqtt/config.yaml.default

if [ ! -f /config/insteon-mqtt/config.yaml ]; then
    echo "Copying default config.yaml"
    /bin/cp /opt/insteon-mqtt/config.yaml /config/insteon-mqtt/config.yaml
fi

python /opt/insteon-mqtt/hassio/start.py /config/insteon-mqtt/config.yaml start
