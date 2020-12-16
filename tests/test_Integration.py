#===========================================================================
#
# Tests for: Integration of Insteon-Mqtt
#
# pylint: disable=attribute-defined-outside-init
#===========================================================================
# This enables testing of the vast majority of the stack.
# In order to work, this does not call the loop.select loop.  So anything
# inside that loop will not be tested.  Similarly the management of the
# network links is also not tested, such as connection issues.  Links will
# not be polled unless you do that yourself.
#
# However, you can simulate an mqtt command and test the resulting message
# that would be written to the PLM.  You can also simulate a write to the PLM
# and test what mqtt messages would be emitted, or what PLM messages are
# sent in response

import time
# from unittest import mock
# from unittest.mock import call
from unittest.mock import patch
# import pytest
import functools
import insteon_mqtt as IM

published_topics = {}
subscribed_topics = {}
written_msgs = []
mqtt_obj = None
modem_obj = None

def serial_write(self, msg_bytes, next_write_time):
    # This captures the messages sent out to the PLM
    written_msgs.append(msg_bytes)

def mqtt_subscribe(self, topic, qos=0, callback=None):
    # This captures the calls to subscribe to topics
    subscribed_topics[topic] = callback

def mqtt_publish(self, topic, payload, qos=0, retain=False):
    published_topics[topic] = payload

def serial_read(data):
    modem_obj.protocol.link.signal_read.emit(modem_obj.protocol.link, data)

def loop_active(self):
    # Prevent the network loop from running
    return False

def config_apply(config, mqtt, modem):
    # Copy the function so we can capture the modem and mqtt links
    global mqtt_obj, modem_obj
    mqtt_obj = mqtt
    modem_obj = modem
    mqtt.load_config(config['mqtt'])
    modem.load_config(config['insteon'])

class mqtt_msg():
    # Used to simulate mqtt messages
    def __init__(self, topic, payload):
        self.topic = topic
        self.payload = payload.encode(encoding='UTF-8')
        self.qos = 0
        self.retain = False

def patch_all(f):
    """Gathers all of our patches to make them easily reusable

    Use the @path_all decorator to call them
    """
    @patch('sys.argv', ["", "config.yaml", "start"])
    @patch('insteon_mqtt.network.Mqtt.subscribe', mqtt_subscribe)
    @patch('insteon_mqtt.network.Mqtt.publish', mqtt_publish)
    @patch('insteon_mqtt.network.Serial.write', serial_write)
    @patch('insteon_mqtt.network.Manager.active', loop_active)
    @patch('insteon_mqtt.config.apply', config_apply)
    @functools.wraps(f)
    def functor(*args, **kwargs):
        return f(*args, **kwargs)
    return functor

def start_insteon_mqtt():
    IM.cmd_line.main()

    # Signal the mqtt link as connected
    # Ths causes the device mqtt objects to subscribe to topics
    mqtt_obj.link.signal_connected.emit(mqtt_obj.link, True)


@patch_all
def test_set_on_roundtrip():
    start_insteon_mqtt()
    # Send on using the set topic
    msg = mqtt_msg('insteon/3a.29.84/set', 'on')
    subscribed_topics['insteon/3a.29.84/set'](None, None, msg)
    # Test resulting PLM message
    assert written_msgs[0].hex() == '02623a29840f11ff'
    # Return PLM ACK
    serial_read(bytes.fromhex('02623a29840f11ff06'))
    # Return the device ACK
    serial_read(bytes.fromhex('02503a298441eee62b11ff'))
    assert published_topics['insteon/3a.29.84/state'] == '{ "state" : "ON", "brightness" : 255 }'


        # Test PLM Busy
        # serial_read(bytes.fromhex('15'))
