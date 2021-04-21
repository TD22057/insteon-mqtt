#===========================================================================
#
# Tests for: insteont_mqtt/mqtt/Mqtt.py
#
# pylint: disable=redefined-outer-name
#===========================================================================
import logging
import pytest
from unittest import mock
import insteon_mqtt as IM
import helpers as H

# Create our MQTT object to test as well as the linked Insteon object and a
# mocked MQTT client to publish to.
@pytest.fixture
def setup(mock_paho_mqtt):
    link = IM.network.Mqtt()
    mqttModem = H.mqtt.MockModem()
    mqtt = IM.mqtt.Mqtt(link, mqttModem)

    return H.Data(mqtt=mqtt, mqttModem=mqttModem, link=link)

@pytest.fixture
def config():
    # The minimum config required for MQTT
    config = {"broker": "127.0.0.2",
              "port": "12345",
              "cmd_topic": "insteon/command"}
    return config

#===========================================================================
class Test_Mqtt:
    #-----------------------------------------------------------------------
    def test_disabled_discovery(self, setup, caplog, config):
        mqtt = setup.get('mqtt')

        with caplog.at_level(logging.DEBUG):
            # No config
            mqtt.load_config(config)
            assert 'Discovery disabled' in caplog.text

            # Config is False
            caplog.clear()
            config['enable_discovery'] = False
            mqtt.load_config(config)
            assert 'Discovery disabled' in caplog.text

            # Config is True
            caplog.clear()
            config['enable_discovery'] = True
            mqtt.load_config(config)
            assert 'Discovery disabled' not in caplog.text

    #-----------------------------------------------------------------------
    def test_handle_ha_status(self, setup, caplog):
        mqtt = setup.get('mqtt')
        mqtt.devices = {"test_dev": "test_dev_value"}

        message = MockMqttMessage("fake_topic", "online")
        with mock.patch.object(mqtt, '_publish_device_discovery') as mocked:
            mqtt.handle_ha_status(None, None, message)
            mocked.assert_called_once_with("test_dev_value")

        message = MockMqttMessage("fake_topic", "offline")
        with mock.patch.object(mqtt, '_publish_device_discovery') as mocked:
            mqtt.handle_ha_status(None, None, message)
            mocked.assert_not_called()

        message = MockMqttMessage("fake_topic", "bad_thing")
        caplog.clear()
        with caplog.at_level(logging.WARNING):
            mqtt.handle_ha_status(None, None, message)
            assert 'Unexpected HomeAssistant status message' in caplog.text

    #-----------------------------------------------------------------------
    def test_publish(self, setup, caplog):
        mqtt = setup.get('mqtt')

        mqtt.discovery_enabled = False
        device = MockDiscovery()
        with mock.patch.object(device, 'publish_discovery') as mocked:
            mqtt._publish_device_discovery(device)
            mocked.assert_not_called()

        mqtt.discovery_enabled = True
        device = MockDiscovery()
        with mock.patch.object(device, 'publish_discovery') as mocked:
            mqtt._publish_device_discovery(device)
            mocked.assert_called_once()

class MockMqttMessage():
    """MockMqttMessage, generates a mocked paho mqtt message"""
    def __init__(self, topic, payload):
        self.topic = topic
        self.payload = payload.encode(encoding='UTF-8')

class MockDiscovery():
    """MockDiscovery, simulate a device with discovery"""
    def __init__(self):
        pass

    def publish_discovery(self):
        pass
