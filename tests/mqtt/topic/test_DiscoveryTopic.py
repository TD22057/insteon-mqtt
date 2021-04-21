#===========================================================================
#
# Tests for: insteon_mqtt/mqtt/topic/DiscoveryTopic.py
#
# pylint: disable=redefined-outer-name
#===========================================================================
import logging
from unittest import mock
import pytest
import insteon_mqtt as IM
import helpers as H

# Create the base mqtt object
@pytest.fixture
def discovery(mock_paho_mqtt):
    link = IM.network.Mqtt()
    mqttModem = H.mqtt.MockModem()
    mqtt = IM.mqtt.Mqtt(link, mqttModem)
    # set the default topic base
    mqtt.discovery_topic_base = "homeassistant"

    device = MockDevice()
    discovery = IM.mqtt.topic.DiscoveryTopic(mqtt, device)

    return discovery

#===========================================================================
class Test_DiscoveryTopic:
    #-----------------------------------------------------------------------
    def test_load_discovery_data(self, discovery, caplog):
        # This also fully tests _get_unique_id()

        # test lack of discovery class
        config = {}
        discovery.load_discovery_data(config)
        assert 'Unable to find discovery class' in caplog.text
        caplog.clear()

        # test lack of entities defined
        config['fake_dev'] = {}
        discovery.device.config_extra['discovery_class'] = 'fake_dev'
        discovery.load_discovery_data(config)
        assert 'No discovery_entities defined' in caplog.text
        caplog.clear()

        # test lack of component
        config['fake_dev'] = {'discovery_entities': [{}]}
        discovery.load_discovery_data(config)
        assert 'No component specified in discovery entity' in caplog.text
        caplog.clear()

        # Override data at this point
        discovery.discovery_template_data = mock.Mock(return_value={})

        # test lack of unique id
        config['fake_dev'] = {'discovery_entities': [{
            "component": "switch",
            "config": "{}"
        }]}
        discovery.load_discovery_data(config)
        assert 'Error getting unique_id, skipping entry' in caplog.text
        caplog.clear()

        # test with unique_id
        config['fake_dev'] = {'discovery_entities': [{
            "component": "switch",
            "config": '{"unique_id": "unique"}'
        }]}
        discovery.load_discovery_data(config)
        expected_topic = "homeassistant/switch/11.22.33/unique/config"
        assert discovery.entries[0].topic_str == expected_topic
        discovery.entries = []

        # test with uniq_id
        config['fake_dev'] = {'discovery_entities': [{
            "component": "switch",
            "config": '{"uniq_id": "unique2"}'
        }]}
        discovery.load_discovery_data(config)
        expected_topic = "homeassistant/switch/11.22.33/unique2/config"
        assert discovery.entries[0].topic_str == expected_topic
        discovery.entries = []

        # test bad json
        config['fake_dev'] = {'discovery_entities': [{
            "component": "switch",
            "config": "{'no_single': 'quotes'}"
        }]}
        discovery.load_discovery_data(config)
        expected_topic = "homeassistant/switch/11.22.33/unique2/config"
        assert 'Error parsing config as json' in caplog.text
        caplog.clear()

        # test bad template
        config['fake_dev'] = {'discovery_entities': [{
            "component": "switch",
            "config": "{% if bad_format = 1 %}"
        }]}
        discovery.load_discovery_data(config)
        expected_topic = "homeassistant/switch/11.22.33/unique2/config"
        assert 'Error rendering config template' in caplog.text
        caplog.clear()

class MockDevice:
    def __init__(self):
        self.config_extra = {}
        self.label = "Fake device"
        self.addr = IM.Address("11.22.33")
