#!/bin/sh

/bin/mkdir /config/insteon-mqtt/

/bin/cp /opt/insteon-mqtt/config.yaml /config/insteon-mqtt/config.yaml.default

if [ ! -f /config/insteon-mqtt/config.yaml ]; then
    echo "Copying default config.yaml"
    /bin/cp /opt/insteon-mqtt/config.yaml /config/insteon-mqtt/config.yaml
    sed -i "s/storage: 'data'/storage: '\/config\/insteon-mqtt\/data'/" /config/insteon-mqtt/config.yaml
    sed -i "s/file: \/var\/log\/insteon_mqtt.log/file: \/config\/insteon-mqtt\/insteon_mqtt.log/" /config/insteon-mqtt/config.yaml
fi

python3 /opt/insteon-mqtt/hassio/start.py /config/insteon-mqtt/config.yaml start
