#===========================================================================
#
# Tests for: insteon_mqtt/mqtt/topic/DiscoveryTopic.py
#
# pylint: disable=redefined-outer-name
#===========================================================================
import json
from unittest import mock
import pytest
import insteon_mqtt as IM
import helpers as H

def fixture_setup(tmpdir):
    link = IM.network.Mqtt()
    mqttModem = H.mqtt.MockModem()
    mqtt = IM.mqtt.Mqtt(link, mqttModem)
    # set the default topic base
    mqtt.discovery_topic_base = "homeassistant"

    protocol = H.main.MockProtocol()
    modem = H.main.MockModem(tmpdir)
    addr = IM.Address(0x11, 0x22, 0x33)

    return mqtt, protocol, modem, addr

# Create a base object of 'switch' type
@pytest.fixture
def discovery_switch(mock_paho_mqtt, tmpdir):
    mqtt, protocol, modem, addr = fixture_setup(tmpdir)

    device = IM.device.Switch(protocol, modem, addr)

    return IM.mqtt.topic.DiscoveryTopic(mqtt, device)

# Create a base object of 'fan_linc' type
@pytest.fixture
def discovery_fan(mock_paho_mqtt, tmpdir):
    mqtt, protocol, modem, addr = fixture_setup(tmpdir)

    device = IM.device.FanLinc(protocol, modem, addr)

    return IM.mqtt.topic.DiscoveryTopic(mqtt, device)

#===========================================================================
class Test_DiscoveryTopic:
    #-----------------------------------------------------------------------
    def test_load_discovery_data(self, discovery_switch, caplog):
        # This also fully tests _get_unique_id()
        discovery_switch.mqtt.discovery_enabled = True

        # test lack of discovery class
        config = {}
        discovery_switch.load_discovery_data(config)
        assert 'Unable to find discovery class' in caplog.text
        caplog.clear()

        # request fake class to be used for remaining tests
        discovery_switch.device.config_extra['discovery_class'] = 'fake_dev'

        # test lack of entities defined
        config['fake_dev'] = {}
        discovery_switch.load_discovery_data(config)
        assert 'No discovery_entities defined' in caplog.text
        caplog.clear()

        # test lack of component
        config['fake_dev'] = {'discovery_entities': {
            'test': {},
        }}
        discovery_switch.load_discovery_data(config)
        assert 'No component specified in discovery entity' in caplog.text
        caplog.clear()

        # Override data at this point
        discovery_switch.discovery_template_data = mock.Mock(return_value={})

        # test lack of unique id
        config['fake_dev'] = {'discovery_entities': {
            'test': {
                "component": "switch",
                "config": {},
            },
        }}
        discovery_switch.load_discovery_data(config)
        assert 'Error getting unique_id, skipping entry' in caplog.text
        caplog.clear()

        # test with unique_id
        config['fake_dev'] = {'discovery_entities': {
            'test': {
                "component": "switch",
                "config": {"unique_id": "unique"},
            },
        }}
        discovery_switch.load_discovery_data(config)
        expected_topic = "homeassistant/switch/11_22_33/unique/config"
        assert discovery_switch.disc_templates[0].topic_str == expected_topic
        discovery_switch.disc_templates = []

        # test with uniq_id
        config['fake_dev'] = {'discovery_entities': {
            'test': {
                "component": "switch",
                "config": {"uniq_id": "unique2"},
            },
        }}
        discovery_switch.load_discovery_data(config)
        expected_topic = "homeassistant/switch/11_22_33/unique2/config"
        assert discovery_switch.disc_templates[0].topic_str == expected_topic
        discovery_switch.disc_templates = []

        # test old-style (unnamed) entities
        config['fake_dev'] = {'discovery_entities': [{
            "component": "switch",
            "config": {"unique_id": "unique"}
        }]}
        discovery_switch.load_discovery_data(config)
        expected_topic = "homeassistant/switch/11_22_33/unique/config"
        assert discovery_switch.disc_templates[0].topic_str == expected_topic
        discovery_switch.disc_templates = []

        # test bad json
        config['fake_dev'] = {'discovery_entities': {
            'test': {
                "component": "switch",
                "config": "{'no_single': 'quotes'}",
            },
        }}
        discovery_switch.load_discovery_data(config)
        assert 'Error parsing config as json' in caplog.text
        caplog.clear()

        # test bad template
        config['fake_dev'] = {'discovery_entities': {
            'test': {
                "component": "switch",
                "config": "{% if bad_format = 1 %}",
            },
        }}
        discovery_switch.load_discovery_data(config)
        assert 'Error rendering config template' in caplog.text
        caplog.clear()

        # test discovery suppression (entire device)
        discovery_switch.device.config_extra['discoverable'] = False
        config['fake_dev'] = {'discovery_entities': {
            'test': {
                "component": "switch",
                "config": {"unique_id": "unique"},
            },
        }}
        discovery_switch.load_discovery_data(config)
        assert len(discovery_switch.disc_templates) == 0
        del discovery_switch.device.config_extra['discoverable']

    #-----------------------------------------------------------------------
    def test_load_device_discovery_overrides(self, discovery_fan, caplog):
        discovery_fan.mqtt.discovery_enabled = True
        # build and request fake class to be used for tests
        config = {}
        config['fake_dev'] = {'discovery_entities': {
            'fake': {
                "component": "fan",
                "config": {
                    "unique_id": "unique",
                    "icon": "fake",
                },
            },
        }}
        discovery_fan.device.config_extra['discovery_class'] = 'fake_dev'
        # Override data from this point
        discovery_fan.discovery_template_data = mock.Mock(return_value={})

        # test empty override dict
        discovery_fan.device.config_extra['discovery_overrides'] = {}
        discovery_fan.load_discovery_data(config)
        assert len(discovery_fan.disc_templates) == 1
        discovery_fan.disc_templates = []

        # test empty device override dict
        discovery_fan.device.config_extra['discovery_overrides'] = { 'device': {} }
        discovery_fan.load_discovery_data(config)
        assert len(discovery_fan.disc_templates) == 1
        discovery_fan.disc_templates = []

        # test empty config override dict
        discovery_fan.device.config_extra['discovery_overrides'] = { 'fake': {
            "config": {},
        }}
        discovery_fan.load_discovery_data(config)
        assert len(discovery_fan.disc_templates) == 1
        discovery_fan.disc_templates = []

        # test for non-matching entity name
        discovery_fan.device.config_extra['discovery_overrides'] = { 'fakefail': {
        }}
        discovery_fan.load_discovery_data(config)
        assert 'Entity to override was not found' in caplog.text
        caplog.clear()

        # test for suppressing entity
        discovery_fan.device.config_extra['discovery_overrides'] = { 'fake': {
            "discoverable": False,
        }}
        discovery_fan.load_discovery_data(config)
        assert len(discovery_fan.disc_templates) == 0

        # test for overriding component
        discovery_fan.device.config_extra['discovery_overrides'] = { 'fake': {
           "component": "switch",
        }}
        discovery_fan.load_discovery_data(config)
        expected_topic = "homeassistant/switch/11_22_33/unique/config"
        assert discovery_fan.disc_templates[0].topic_str == expected_topic
        discovery_fan.disc_templates = []

        # test for overriding config unique_id
        discovery_fan.device.config_extra['discovery_overrides'] = { 'fake': {
            "config": {
                "unique_id": "override",
            },
        }}
        discovery_fan.load_discovery_data(config)
        expected_topic = "homeassistant/fan/11_22_33/override/config"
        assert discovery_fan.disc_templates[0].topic_str == expected_topic
        discovery_fan.disc_templates = []

        # test for adding config attribute
        discovery_fan.device.config_extra['discovery_overrides'] = { 'fake': {
            "config": {
                "foo": "fake",
            },
        }}
        discovery_fan.load_discovery_data(config)
        payload = json.loads(discovery_fan.disc_templates[0].payload_str)
        assert payload.get("foo", None) == "fake"
        discovery_fan.disc_templates = []

        # test for deleting config attribute
        discovery_fan.device.config_extra['discovery_overrides'] = { 'fake': {
            "config": {
                "icon": "",
            },
        }}
        discovery_fan.load_discovery_data(config)
        payload = json.loads(discovery_fan.disc_templates[0].payload_str)
        assert "icon" not in payload
        discovery_fan.disc_templates = []

        # test for overriding device info
        discovery_fan.device_info_template = {"info": "fake"}
        discovery_fan.device.config_extra['discovery_overrides'] = { 'device': {
            "info": "override",
        }}
        discovery_fan.load_discovery_data(config)
        assert discovery_fan.device_info_template.get("info", None) == "override"
        discovery_fan.disc_templates = []

        # test for adding device info
        discovery_fan.device_info_template = {"info": "fake"}
        discovery_fan.device.config_extra['discovery_overrides'] = { 'device': {
            "sa": "fake",
        }}
        discovery_fan.load_discovery_data(config)
        assert discovery_fan.device_info_template.get("info", None) == "fake"
        assert discovery_fan.device_info_template.get("sa", None) == "fake"
        discovery_fan.disc_templates = []

        # test for deletng device info
        discovery_fan.device_info_template = {"info": "fake"}
        discovery_fan.device.config_extra['discovery_overrides'] = { 'device': {
            "mdl": "",
        }}
        discovery_fan.load_discovery_data(config)
        assert "mdl" not in discovery_fan.device_info_template
        discovery_fan.disc_templates = []

        # test for suppressing one of multiple entities
        config['fake_dev'] = {'discovery_entities': {
            'fake': {
                "component": "fan",
                "config": {
                    "unique_id": "unique",
                },
            },
            'extra': {
                "component": "light",
                "config": {
                    "unique_id": "unique",
                },
            },
        }}
        discovery_fan.device.config_extra['discovery_overrides'] = { 'fake': {
            "discoverable": False,
        }}
        discovery_fan.load_discovery_data(config)
        assert len(discovery_fan.disc_templates) == 1


    #-----------------------------------------------------------------------
    def test_load_class_discovery_overrides(self, discovery_fan):
        discovery_fan.mqtt.discovery_enabled = True
        # build fake class to be used for tests
        config = {}
        config['fake_dev'] = {'discovery_entities': {
            'fake': {
                "component": "fan",
                "config": {"unique_id": "unique"},
            },
        }}
        discovery_fan.device.config_extra['discovery_class'] = ['fake_dev']
        # Override data from this point
        discovery_fan.discovery_template_data = mock.Mock(return_value={})

        # test base
        discovery_fan.load_discovery_data(config)
        expected_topic = "homeassistant/fan/11_22_33/unique/config"
        assert discovery_fan.disc_templates[0].topic_str == expected_topic
        discovery_fan.disc_templates = []

        # test with one discovery_class containing overrides
        config['fake_override'] = {'discovery_overrides': {
            'fake': {
                "config": {
                    "unique_id": "override",
                },
            },
        }}
        discovery_fan.device.config_extra['discovery_override_class'] = 'fake_override'
        discovery_fan.load_discovery_data(config)
        expected_topic = "homeassistant/fan/11_22_33/override/config"
        assert discovery_fan.disc_templates[0].topic_str == expected_topic
        discovery_fan.disc_templates = []

        # test with multiple discovery_class containing overrides
        config['fake_override1'] = {'discovery_overrides': {
            'fake': {
                "config": {
                    "unique_id": "override",
                },
            },
        }}
        config['fake_override2'] = {'discovery_overrides': {
            'fake': {
                "component": "light",
                "config": {
                    "unique_id": "override2",
                },
            },
        }}
        discovery_fan.device.config_extra['discovery_override_class'] = ['fake_override1', 'fake_override2']
        discovery_fan.load_discovery_data(config)
        expected_topic = "homeassistant/light/11_22_33/override2/config"
        assert discovery_fan.disc_templates[0].topic_str == expected_topic
        discovery_fan.disc_templates = []

        # test with multiple discovery_class containing suppressions
        config['fake_override1'] = {'discovery_overrides': {
            'fake': {
                "discoverable": False,
            },
        }}
        config['fake_override2'] = {'discovery_overrides': {
            'fake': {
                "discoverable": False,
            },
        }}
        discovery_fan.device.config_extra['discovery_override_class'] = ['fake_override1', 'fake_override2']
        discovery_fan.load_discovery_data(config)
        assert len(discovery_fan.disc_templates) == 0

    #-----------------------------------------------------------------------
    def test_template_data(self, discovery_switch, caplog):
        # Test default values
        data = discovery_switch.discovery_template_data()
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
        assert data['device_info'] == "{}"

        # Test with actual values
        discovery_switch.device.name = "test device"
        discovery_switch.device.name_user_case = "Test Device"
        discovery_switch.device.db.engine = 2
        discovery_switch.device.db.desc = IM.catalog.find(0x02, 0x2a)
        discovery_switch.device.db.firmware = 0x45
        data = discovery_switch.discovery_template_data()
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
        assert data['device_info'] == "{}"

        # test device info template
        discovery_switch.device_info_template = {
            "ids": "{{address}}",
            "mf": "Insteon",
            "mdl": "{%- if model_number != 'Unknown' -%}"
                     "{{model_number}} - {{model_description}}"
                   "{%- elif dev_cat_name != 'Unknown' -%}"
                     "{{dev_cat_name}} - 0x{{'%0x' % sub_cat|int }}"
                   "{%- elif dev_cat == 0 and sub_cat == 0 -%}"
                     "No Info"
                   "{%- else -%}"
                     "0x{{'%0x' % dev_cat|int }} - 0x{{'%0x' % sub_cat|int }}"
                   "{%- endif -%}",
            "sw": "0x{{'%0x' % firmware|int }} - {{engine}}",
            "name": "{{name_user_case}}",
            "via_device": "{{modem_addr}}",
        }

        data = discovery_switch.discovery_template_data()
        assert data['device_info'] == \
"""{
  "ids": "11.22.33",
  "mf": "Insteon",
  "mdl": "2477S - SwitchLinc Relay (Dual-Band)",
  "sw": "0x45 - i2cs",
  "name": "Test Device",
  "via_device": "20.30.40"
}"""

        # test bad device info template
        discovery_switch.device_info_template = {
            "bad": "{% if bad = 1 %}"
        }
        data = discovery_switch.discovery_template_data()
        assert 'Error rendering device_info_template' in caplog.text
        caplog.clear()

    #-----------------------------------------------------------------------
    def test_device_info(self, discovery_fan):
        discovery_fan.mqtt.discovery_enabled = True
        # build and request fake class to be used for tests
        config = {}
        discovery_fan.device_info_template = {
            "fake": "fake_device"
        }
        discovery_fan.device.config_extra['discovery_class'] = 'fake_dev'

        # test with 'device_info' in entity config
        config['fake_dev'] = {'discovery_entities': {
            'fake': {
                "component": "fan",
                "config": {
                    "unique_id": "unique",
                    "device": "{{device_info}}",
                },
            },
        }}
        discovery_fan.load_discovery_data(config)
        payload = discovery_fan.disc_templates[0].render_payload(discovery_fan.discovery_template_data(), silent=True)
        assert payload == \
"""{
  "unique_id": "unique",
  "device": {
  "fake": "fake_device"
}
}"""
        discovery_fan.disc_templates = []

        # test with 'device_info_template' in string-stlye entity config
        config['fake_dev'] = {'discovery_entities': {
            'fake': {
                "component": "fan",
                "config": '{"unique_id": "unique", "device": {{device_info_template}}}',
            },
        }}
        discovery_fan.load_discovery_data(config)
        payload = discovery_fan.disc_templates[0].render_payload(discovery_fan.discovery_template_data(), silent=True)
        assert payload == \
"""{"unique_id": "unique", "device": {
  "fake": "fake_device"
}}"""
        discovery_fan.disc_templates = []

    #-----------------------------------------------------------------------
    @mock.patch('time.time', mock.MagicMock(return_value=12345))
    def test_publish(self, discovery_switch):
        discovery_switch.disc_templates.append(mock.Mock())
        discovery_switch.publish_discovery()
        data = {
            'address': '11.22.33',
            'availability_topic': '',
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
            'device_info': '{}',
            # alias to support old configurations
            'device_info_template': '{}',
            'timestamp': 12345,
        }
        discovery_switch.disc_templates[0].publish.assert_called_once_with(
            discovery_switch.mqtt,
            data,
            retain=False
        )
