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
plm_link = None
insteon = None

def patch_insteon_mqtt(args, cfg):
    """A lightly modified start command

    Mainly removes the loop of loop.select()
    Also signals a connection of the mqtt client
    """
    global plm_link, insteon

    # Always log to the screen if a file isn't active.
    if not args.log:
        args.log_screen = True

    # Initialize the logging system either using the command line
    # inputs or the config file.  If these vars are None, then the
    # config file logging data is used.
    IM.log.initialize(args.level, args.log_screen, args.log, config=cfg)

    # Create the network event loop and MQTT and serial modem clients.
    loop = IM.network.Manager()
    mqtt_link = IM.network.Mqtt()
    plm_link = IM.network.Serial()
    stack_link = IM.network.Stack()
    timed_link = IM.network.TimedCall()

    # Add the clients to the event loop.
    loop.add(mqtt_link, connected=False)
    loop.add(plm_link, connected=False)
    loop.add_poll(stack_link)
    loop.add_poll(timed_link)

    # Create the insteon message protocol, modem, and MQTT handler and
    # link them together.
    insteon = IM.Protocol(plm_link)
    modem = IM.Modem(insteon, stack_link, timed_link)
    mqtt_handler = IM.mqtt.Mqtt(mqtt_link, modem)

    # Load the configuration data into the objects.
    IM.config.apply(cfg, mqtt_handler, modem)

    # Signal the mqtt link as connected
    # Ths causes the device mqtt objects to subscribe to topics
    mqtt_link.signal_connected.emit(mqtt_link, True)

def serial_write(self, msg_bytes, next_write_time):
    # This captures the messages sent out to the PLM
    written_msgs.append(msg_bytes)

def mqtt_subscribe(self, topic, qos=0, callback=None):
    # This captures the calls to subscribe to topics
    subscribed_topics[topic] = callback

def mqtt_publish(self, topic, payload, qos=0, retain=False):
    published_topics[topic] = payload

def serial_read(data):
    plm_link.signal_read.emit(plm_link, data)

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
    @patch('insteon_mqtt.cmd_line.start.start', patch_insteon_mqtt)
    @patch('insteon_mqtt.network.Mqtt.subscribe', mqtt_subscribe)
    @patch('insteon_mqtt.network.Mqtt.publish', mqtt_publish)
    @patch('insteon_mqtt.network.Serial.write', serial_write)
    @functools.wraps(f)
    def functor(*args, **kwargs):
        return f(*args, **kwargs)
    return functor

def start_insteon_mqtt():
    IM.cmd_line.main()

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
