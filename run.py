#!/usr/bin/env python

import insteon_mqtt as IM
import logging
import yaml

logging.basicConfig(level=logging.DEBUG, datefmt='%Y-%m-%d %H:%M:%S',
                    format='%(asctime)s %(levelname)s %(module)s: %(message)s')

loop = IM.network.Manager()
mqtt_link = IM.network.Mqtt()
plm_link = IM.network.Serial()

loop.add(mqtt_link, connected=False)
loop.add(plm_link, connected=False)

insteon = IM.Protocol(plm_link)
modem = IM.Modem(insteon)
mqtt = IM.mqtt.Mqtt(mqtt_link, modem)

IM.config.load("config.yaml", mqtt, modem)

while loop.active():
    loop.select()
