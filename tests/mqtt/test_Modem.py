#===========================================================================
#
# Tests for: insteont_mqtt/mqtt/Modem.py
#
# pylint: disable=redefined-outer-name
#===========================================================================
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
    modem = IM.Modem(proto)
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
    def test_template(self, setup):
        mdev, addr, name = setup.getAll(['mdev', 'addr', 'name'])

        data = mdev.template_data()
        right = {"address" : addr.hex, "name" : name}
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


#===========================================================================
