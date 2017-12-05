#!/usr/bin/env python

import insteon_mqtt as IM
import yaml

# Read the config first - that configures the logging system.
config = IM.config.load("config.yaml")
IM.log.initialize(config=config)

loop = IM.network.Manager()
mqtt_link = IM.network.Mqtt()
plm_link = IM.network.Serial()

loop.add(mqtt_link, connected=False)
loop.add(plm_link, connected=False)

insteon = IM.Protocol(plm_link)
modem = IM.Modem(insteon)
mqtt = IM.mqtt.Mqtt(mqtt_link, modem)

# Load the configuration data into the objects.
IM.config.apply(config, mqtt, modem)

# Start the network event loop.
while loop.active():
    loop.select()
