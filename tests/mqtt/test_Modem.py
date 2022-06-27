#===========================================================================
#
# Tests for: insteont_mqtt/mqtt/Modem.py
#
# pylint: disable=redefined-outer-name
#===========================================================================
from unittest import mock
import pytest
import insteon_mqtt as IM
import helpers as H

# NOTE about mocking: Don't mock classes directly being used by the class
# being tested.  If we do that, then we're not testing whether the class
# actually works with the class it depends on.  For example, let's say we're
# testing class A which depends on B and C.  If we mock B and C and then
# later the API's for B and C change, the test will still pass because in the
# test those are fake interfaces.  Part of what the test or A needs to catch
# are changes in classes that A depends on not being updated in A.  So the
# correct test pattern is to always use the actual classes that A depends on
# and mock the classees that those dependencies depend on.


# Create our MQTT object to test as well as the linked Insteon object and a
# mocked MQTT client to publish to.
@pytest.fixture
def setup(mock_paho_mqtt, tmpdir):
    proto = H.main.MockProtocol()
    modem = IM.Modem(proto, IM.network.Stack(), IM.network.TimedCall())
    modem.name = "modem"
    modem.addr = IM.Address(0x20, 0x30, 0x40)

    link = IM.network.Mqtt()
    mqtt = IM.mqtt.Mqtt(link, modem)
    mdev = IM.mqtt.Modem(mqtt, modem)

    return H.Data(addr=modem.addr, name=modem.name, link=link,
                        mdev=mdev, proto=proto)


#===========================================================================
class Test_Modem:
    #-----------------------------------------------------------------------
    def test_pubsub(self, setup):
        mdev, link = setup.getAll(['mdev', 'link'])

        mdev.subscribe(link, 2)
        assert len(link.client.sub) == 1
        assert link.client.sub[0] == dict(
            topic='insteon/modem/scene', qos=2)

        mdev.unsubscribe(link)
        assert len(link.client.unsub) == 1
        assert link.client.unsub[0] == dict(
            topic='insteon/modem/scene')

    #-----------------------------------------------------------------------
    @mock.patch('time.time', mock.MagicMock(return_value=12345))
    def test_template(self, setup):
        mdev, addr, name = setup.getAll(['mdev', 'addr', 'name'])

        data = mdev.base_template_data()
        right = {"address" : addr.hex, "name" : name, "timestamp": 12345}
        assert data == right

    #-----------------------------------------------------------------------
    def test_input_scene(self, setup):
        mdev, link, proto = setup.getAll(['mdev', 'link', 'proto'])
        mdev.load_config({})

        qos = 2
        config = {'modem' : {
            'scene_topic' : 'foo/modem',
            'scene_payload' : ('{ "cmd" : "{{json.run}}", '
                               '"group" : {{json.grp}}}')}}
        mdev.load_config(config, qos=qos)

        mdev.subscribe(link, qos)
        topic = 'foo/modem'

        payload = b'{ "run" : "OFF", "grp" : 5 }'
        link.publish(topic, payload, qos, retain=False)
        assert len(proto.sent) == 1

        assert proto.sent[0].msg.cmd1 == 0x13
        assert proto.sent[0].msg.group == 5
        proto.clear()

        payload = b'{ "run" : "ON", "grp" : 10 }'
        link.publish(topic, payload, qos, retain=False)
        assert len(proto.sent) == 1

        assert proto.sent[0].msg.cmd1 == 0x11
        assert proto.sent[0].msg.group == 10
        proto.clear()

        # test error payload
        link.publish(topic, b'asdf', qos, False)

    #-----------------------------------------------------------------------
    def test_discovery(self, setup):
        mdev, link = setup.getAll(['mdev', 'link'])
        topic = "insteon/%s" % setup.addr.hex

        # Modem with no scenes should have no discovery topics
        mdev.load_config({"modem": {"junk": "junk"}})
        assert mdev.default_discovery_cls == "modem"
        assert mdev.rendered_topic_map == {
            'scene_topic': 'insteon/modem/scene'
        }
        assert len(mdev.extra_topic_nums) == 0

    #-----------------------------------------------------------------------
    @mock.patch('time.time', mock.MagicMock(return_value=12345))
    def test_discovery_publish(self, setup):
        mdev, link = setup.getAll(['mdev', 'link'])

        # First generate our discovery template
        unique_id = "{{address}}_{{scene}}"
        topic = "homeassistant/switch/%s/%s/config" % (
            setup.addr.hex,
            unique_id
        )
        payload = """
          {
            "uniq_id": "{{address}}_{{scene}}",
            "name": "{%- if scene_name != "" -%}
                       {{scene_name}}
                     {%- else -%}
                       Modem Scene {{scene}}
                     {%- endif -%}",
            "cmd_t": "{{scene_topic}}",
            "device": {{device_info}},
            "payload_on": "{\"cmd\": \"on\", \"group\": \"{{scene}}\"}",
            "payload_off": "{\"cmd\": \"off\", \"group\": \"{{scene}}\"}"
          }
        """
        mdev.disc_templates.append(IM.mqtt.MsgTemplate(topic=topic,
                                                       payload=payload,
                                                       qos=1,
                                                       retain=False))

        # Second add some fake groups
        mdev.device.db.groups[1] = ['junk']
        mdev.device.db.groups[2] = ['junk']
        mdev.device.db.groups[0x10] = ['junk']

        # Third add a name to one of the fake groups
        mdev.device.scene_map['test_name'] = 0x10

        # Fourth, mock the publish call on MsgTemplate
        mdev.disc_templates[0].publish = mock.Mock()
        mocked = mdev.disc_templates[0].publish

        # Finally call publish_discovery() and test results
        mdev.publish_discovery()
        assert mocked.call_count == 2

        # The expected template data
        data = {
            'address': '20.30.40',
            'availability_topic': '',
            'dev_cat': 0,
            'dev_cat_name': 'Unknown',
            'device_info': '{}',
            'device_info_template': '{}',
            'engine': 'Unknown',
            'firmware': 0,
            'model_description': 'Unknown',
            'model_number': 'Unknown',
            'modem_addr': '20.30.40',
            'name': 'modem',
            'name_user_case': 'Modem',
            'scene': 0,
            'scene_name': '',
            'sub_cat': 0,
            'timestamp': 12345
        }


        # One call should be group 2 with no name
        data['scene'] = 2
        mocked.assert_any_call(mdev.mqtt, data, retain=False)

        # Other call should be group 16 with name of 'test_name'
        data['scene'] = 16
        data['scene_name'] = 'test_name'
        mocked.assert_any_call(mdev.mqtt, data, retain=False)


#===========================================================================
