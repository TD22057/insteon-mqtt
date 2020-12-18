#===========================================================================
#
# Tests for: Integration of Insteon-Mqtt
#
# pylint: disable=attribute-defined-outside-init
#===========================================================================
"""This enables integration testing of Insteon-Mqtt

This is not a replacement for unit testing.  It is useful for testing the
interactions between the entire stack.

To use, simply pass the stack fixture as an argument to any test.  Then use
the stack.publish_to_mqtt() and stack.write_to_modem() methods to simulate
messages sent to the mqtt server or modem.

Tests can be performed on stack.written_msgs and stack.published_topics

Each test function will create and tear down a full stack fixture.  So use
sparingly to decrease testing times.

The test devices are created from the sample config.yaml file included in the
base directory

"""
from unittest.mock import patch
import pytest
import json
from insteon_mqtt import log
import insteon_mqtt as IM


def test_set_on_functions(stack):
    #-----------------------
    # Test the on command
    # Send on using the set topic, 3a.29.84 is a switch
    stack.publish_to_mqtt('insteon/3a.29.84/set', 'on')
    # Test resulting PLM message
    assert stack.written_msgs[0] == '02623a29840f11ff'
    # Return PLM ACK
    stack.write_to_modem('02623a29840f11ff06')
    # Return the device ACK
    stack.write_to_modem('02503a298441eee62b11ff')
    assert stack.published_topics['insteon/3a.29.84/state'] == 'ON'

    #-----------------------
    # Test the level command
    payload = json.dumps({"state" : 'ON', "brightness" : 127})
    stack.publish_to_mqtt('insteon/12.29.84/level', payload)
    # Test resulting PLM message
    assert stack.written_msgs[1] == '02621229840f117f'
    # Return PLM ACK
    stack.write_to_modem('02621229840f117f06')
    # Return the device ACK   1229840f117f06
    stack.write_to_modem('025012298441eee62b117f')
    assert (stack.published_topics['insteon/12.29.84/state'] ==
            '{ "state" : "ON", "brightness" : 127 }')


# ===============================================================
@pytest.fixture
def stack():
    return Patch_Stack()

class Patch_Stack():
    def __init__(self):
        # Contains an array of all messages sent by the modem messages are
        # stored as strings with hexadecimal characters
        self.written_msgs = []
        # Contains a dictionary of the most recent messages sent to each
        # topic, wherein the keys are the topic names
        self.published_topics = {}
        self._subscribed_topics = {}
        self.mqtt_obj = None
        self.modem_obj = None

        @patch('insteon_mqtt.network.Mqtt.subscribe', self._mqtt_subscribe)
        @patch('insteon_mqtt.config.apply', self._config_apply)
        @patch('sys.argv', ["", "config.yaml", "start"])
        @patch.object(IM.network.Manager, 'active', return_value=False)
        @patch.object(log, 'initialize')
        def start(*args):
            IM.cmd_line.main()
            # Signal the mqtt link as connected
            # Ths causes the device mqtt objects to subscribe to topics
            self.mqtt_obj.link.signal_connected.emit(self.mqtt_obj.link, True)

        start()

    @property
    def plm_link(self):
        return self.modem_obj.protocol.link

    def _mqtt_subscribe(self, topic, qos=0, callback=None):
        # This captures the calls to subscribe to topics that occur in
        # __init__.start
        self._subscribed_topics[topic] = callback

    def _config_apply(self, config, mqtt, modem):
        # Copy the function so we can capture the modem and mqtt links
        self.mqtt_obj = mqtt
        self.modem_obj = modem
        mqtt.load_config(config['mqtt'])
        modem.load_config(config['insteon'])

    def publish_to_mqtt(self, topic, payload):
        """Simulate sending an mqtt message

        Args:
          topic:   (str) the mqtt topic to write to
          payload: (str) the payload sent to the topic
        """
        msg_obj = self.mqtt_msg(topic, payload)
        with patch('insteon_mqtt.network.Serial.write', self._modem_out):
            self._subscribed_topics[topic](None, None, msg_obj)

    def _modem_out(self, msg_bytes, next_write_time):
        # This captures the messages sent out to the PLM
        self.written_msgs.append(msg_bytes.hex())

    def write_to_modem(self, data):
        """Simulate the modem receiving a message

        Args:
          data: (str) a string of hexadecimal characters that the modem will
                receive
        """
        data = bytes.fromhex(data)
        with patch('insteon_mqtt.network.Mqtt.publish', self._mqtt_publish):
            self.plm_link.signal_read.emit(self.plm_link, data)

    def _mqtt_publish(self, topic, payload, qos=0, retain=False):
        # This captures mqtt messages emitted
        self.published_topics[topic] = payload

    class mqtt_msg():
        # Used to simulate mqtt messages
        def __init__(self, topic, payload):
            self.topic = topic
            self.payload = payload.encode(encoding='UTF-8')
            self.qos = 0
            self.retain = False
