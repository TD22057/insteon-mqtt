#!/usr/bin/env python

import insteon_mqtt as IM
import logging
import yaml

logging.basicConfig(level=logging.DEBUG)

config = yaml.load(open("config.yaml").read())

loop = IM.network.poll.Manager()
mqtt_link = IM.network.Mqtt( '127.0.0.1' )
plm_link = IM.network.Serial( '/dev/insteon' )

loop.add(mqtt_link, connected=False)
loop.add(plm_link, connected=False)

insteon = IM.Protocol(plm_link)
modem = IM.Modem(insteon)
mqtt = IM.Mqtt(mqtt_link, modem)

modem.load_config(config['insteon'])
mqtt.load_config(config['mqtt'])

while loop.active():
    loop.select()

    
