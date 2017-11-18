#!/usr/bin/env python

import insteon_mqtt as IM
import logging
import yaml

logging.basicConfig(level=logging.DEBUG, datefmt='%Y-%m-%d %H:%M:%S',
                    format='%(asctime)s %(levelname)s %(module)s: %(message)s')

config = yaml.load(open("config.yaml").read())

loop = IM.network.Manager()
mqtt_link = IM.network.Mqtt()
plm_link = IM.network.Serial()

loop.add(mqtt_link, connected=False)
loop.add(plm_link, connected=False)

insteon = IM.Protocol(plm_link)
modem = IM.Modem(insteon)
mqtt = IM.Mqtt(mqtt_link, modem)

modem.load_config(config['insteon'])
mqtt.load_config(config['mqtt'])

while loop.active():
    loop.select()
