#!/bin/sh

/bin/cp /opt/insteon-mqtt/config-example.yaml /config/config.yaml.default

# Migrate add-on data from the Home Assistant config folder,
# to the add-on configuration folder.
# We add a file to the old directory so that hopefully a user
# doesn't get confused in the future.
if [ ! -f /config/config.yaml ] && [ -f /homeassistant/insteon-mqtt/config.yaml]; then
    shopt -s dotglob
    mv /homeassistant/insteon-mqtt/* /config/ \
        || echo "Failed to migrate InsteonMQTT configuration"; exit 1;
    cp /opt/insteon-mqtt/hassio/CONFIG-MOVED.txt /homeassistant/insteon-mqtt/CONFIG-MOVED.txt
    sed -i "s/<<MIGRATION_DATE>>/$(date)/g" /homeassistant/insteon-mqtt/CONFIG-MOVED.txt
    echo "InsteonMQTT configuration successfully migrated from /config/insteon-mqtt."
fi

if [ ! -f /config/config.yaml ]; then
    echo "Welcome to InsteonMQTT!"
    echo "Creating your initial config.yaml file."
    /bin/cp /config/config.yaml.default /config/config.yaml \
      || echo "Unable to create initial InsteonMQTT config.yaml file"; exit 1;
    sed -i "s|#storage: 'data'|storage: '/config/data'|" /config/config.yaml
    sed -i "s|#file: /var/log/insteon_mqtt.log|file: /config/insteon_mqtt.log|" /config/config.yaml
    echo "Please define the required settings in the file /config/config.yaml"
    echo "(which can be found at '/addons_configs/83fc19e1_insteon-mqtt/config.yaml'"
    echo "within VSCode or SSH Addon)."
    echo "Then you can start InsteonMQTT."
else
    python3 /opt/insteon-mqtt/hassio/start.py /config/config.yaml start
fi
