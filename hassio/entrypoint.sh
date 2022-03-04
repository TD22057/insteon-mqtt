#!/bin/sh

/bin/mkdir /config/insteon-mqtt/

/bin/cp /opt/insteon-mqtt/config-example.yaml /config/insteon-mqtt/config.yaml.default

if [ ! -f /config/insteon-mqtt/config.yaml ]; then
    echo "Welcome to InsteonMQTT!"
    echo "Creating your initial config.yaml file."
    /bin/cp /config/insteon-mqtt/config.yaml.default /config/insteon-mqtt/config.yaml
    sed -i "s/#storage: 'data'/storage: '\/config\/insteon-mqtt\/data'/" /config/insteon-mqtt/config.yaml
    sed -i "s/#file: \/var\/log\/insteon_mqtt.log/file: \/config\/insteon-mqtt\/insteon_mqtt.log/" /config/insteon-mqtt/config.yaml
    echo "Please edit the file /config/insteon-mqtt/config.yaml"
    echo "Then you can start InsteonMQTT."
else
    python3 /opt/insteon-mqtt/hassio/start.py /config/insteon-mqtt/config.yaml start
fi
