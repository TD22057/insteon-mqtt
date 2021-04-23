#===========================================================================
#
# Tests for: insteon_mqtt/mqtt/topic/DiscoveryTopic.py
#
# pylint: disable=redefined-outer-name
#===========================================================================
from unittest import mock
import pytest
import insteon_mqtt as IM
import helpers as H

# Create the base mqtt object
@pytest.fixture
def discovery(mock_paho_mqtt, tmpdir):
    link = IM.network.Mqtt()
    mqttModem = H.mqtt.MockModem()
    mqtt = IM.mqtt.Mqtt(link, mqttModem)
    # set the default topic base
    mqtt.discovery_topic_base = "homeassistant"

    protocol = H.main.MockProtocol()
    modem = H.main.MockModem(tmpdir)
    addr = IM.Address(0x11, 0x22, 0x33)
    device = IM.device.Switch(protocol, modem, addr)
    discovery = IM.mqtt.topic.DiscoveryTopic(mqtt, device)

    return discovery

#===========================================================================
class Test_DiscoveryTopic:
    #-----------------------------------------------------------------------
    def test_load_discovery_data(self, discovery, caplog):
        # This also fully tests _get_unique_id()
        discovery.mqtt.discovery_enabled = True

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
        assert discovery.disc_templates[0].topic_str == expected_topic
        discovery.disc_templates = []

        # test with uniq_id
        config['fake_dev'] = {'discovery_entities': [{
            "component": "switch",
            "config": '{"uniq_id": "unique2"}'
        }]}
        discovery.load_discovery_data(config)
        expected_topic = "homeassistant/switch/11.22.33/unique2/config"
        assert discovery.disc_templates[0].topic_str == expected_topic
        discovery.disc_templates = []

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

    #-----------------------------------------------------------------------
    def test_template_data(self, discovery, caplog):
        # Test default values
        data = discovery.discovery_template_data()
        assert data['address'] == "11.22.33"
        assert data['name'] == "11.22.33"
        assert data['name_user_case'] == "11.22.33"
        assert data['engine'] == "Unknown"
        assert data['model_number'] == 'Unknown'
        assert data['model_description'] == 'Unknown'
        assert data['dev_cat_name'] == 'Unknown'
        assert data['dev_cat'] == 0
        assert data['sub_cat'] == 0
        assert data['firmware'] == 0
        assert data['modem_addr'] == "20.30.40"
        assert data['device_info_template'] == ""

        # Test with actual values
        discovery.device.name = "test device"
        discovery.device.name_user_case = "Test Device"
        discovery.device.db.engine = 2
        discovery.device.db.desc = IM.catalog.find(0x02, 0x2a)
        discovery.device.db.firmware = 0x45
        data = discovery.discovery_template_data()
        assert data['name'] == "test device"
        assert data['name_user_case'] == "Test Device"
        assert data['engine'] == "i2cs"
        assert data['model_number'] == '2477S'
        assert data['model_description'] == 'SwitchLinc Relay (Dual-Band)'
        assert data['dev_cat_name'] == 'SWITCHED_LIGHTING'
        assert data['dev_cat'] == 0x02
        assert data['sub_cat'] == 0x2a
        assert data['firmware'] == 0x45
        assert data['modem_addr'] == "20.30.40"
        assert data['device_info_template'] == ""

        # test device info template
        discovery.mqtt.device_info_template = """
            {
              "ids": "{{address}}",
              "mf": "Insteon",
              "mdl": "{%- if model_number != 'Unknown' -%}
                        {{model_number}} - {{model_description}}
                      {%- elif dev_cat_name != 'Unknown' -%}
                        {{dev_cat_name}} - 0x{{'%0x' % sub_cat|int }}
                      {%- elif dev_cat == 0 and sub_cat == 0 -%}
                        No Info
                      {%- else -%}
                        0x{{'%0x' % dev_cat|int }} - 0x{{'%0x' % sub_cat|int }}
                      {%- endif -%}",
              "sw": "0x{{'%0x' % firmware|int }} - {{engine}}",
              "name": "{{name_user_case}}",
              "via_device": "{{modem_addr}}"
            }
        """
        data = discovery.discovery_template_data()
        assert data['device_info_template'] == """
            {
              "ids": "11.22.33",
              "mf": "Insteon",
              "mdl": "2477S - SwitchLinc Relay (Dual-Band)",
              "sw": "0x45 - i2cs",
              "name": "Test Device",
              "via_device": "20.30.40"
            }
        """

        # test bad device info template
        discovery.mqtt.device_info_template = " {% if bad = 1 %}"
        data = discovery.discovery_template_data()
        assert 'Error rendering device_info_template' in caplog.text
        caplog.clear()

    #-----------------------------------------------------------------------
    def test_publish(self, discovery, caplog):
        discovery.disc_templates.append(mock.Mock())
        discovery.publish_discovery()
        data = {'address': '11.22.33',
                'name': '11.22.33',
                'name_user_case': '11.22.33',
                'engine': 'Unknown',
                'model_number': 'Unknown',
                'model_description': 'Unknown',
                'dev_cat': 0,
                'dev_cat_name': 'Unknown',
                'sub_cat': 0,
                'firmware': 0,
                'modem_addr': '20.30.40',
                'device_info_template': ''}
        discovery.disc_templates[0].publish.assert_called_once_with(
            discovery.mqtt,
            data,
            retain=False
        )
