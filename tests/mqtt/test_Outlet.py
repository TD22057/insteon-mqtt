#===========================================================================
#
# Tests for: insteont_mqtt/mqtt/Outlet.py
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
    modem = H.main.MockModem(tmpdir)
    addr = IM.Address(1, 2, 3)
    name = "device name"
    dev = IM.device.Outlet(proto, modem, addr, name)

    link = IM.network.Mqtt()
    mqttModem = H.mqtt.MockModem()
    mqtt = IM.mqtt.Mqtt(link, mqttModem)
    mdev = IM.mqtt.Outlet(mqtt, dev)

    return H.Data(addr=addr, name=name, dev=dev, mdev=mdev, link=link,
                        proto=proto)


#===========================================================================
class Test_Outlet:
    #-----------------------------------------------------------------------
    def test_pubsub(self, setup):
        mdev, addr, link = setup.getAll(['mdev', 'addr', 'link'])

        mdev.subscribe(link, 2)
        assert len(link.client.sub) == 4
        assert link.client.sub[0] == dict(
            topic='insteon/%s/set/1' % addr.hex, qos=2)
        assert link.client.sub[1] == dict(
            topic='insteon/%s/scene/1' % addr.hex, qos=2)
        assert link.client.sub[2] == dict(
            topic='insteon/%s/set/2' % addr.hex, qos=2)
        assert link.client.sub[3] == dict(
            topic='insteon/%s/scene/2' % addr.hex, qos=2)

        mdev.unsubscribe(link)
        assert len(link.client.unsub) == 4
        assert link.client.unsub[0] == dict(
            topic='insteon/%s/set/1' % addr.hex)
        assert link.client.unsub[1] == dict(
            topic='insteon/%s/scene/1' % addr.hex)
        assert link.client.unsub[2] == dict(
            topic='insteon/%s/set/2' % addr.hex)
        assert link.client.unsub[3] == dict(
            topic='insteon/%s/scene/2' % addr.hex)

    #-----------------------------------------------------------------------
    def test_template(self, setup):
        mdev, addr, name = setup.getAll(['mdev', 'addr', 'name'])

        data = mdev.template_data()
        right = {"address" : addr.hex, "name" : name}
        assert data == right

        data = mdev.template_data(is_on=True, button=1,
                                  mode=IM.on_off.Mode.FAST)
        right = {"address" : addr.hex, "name" : name, "button" : 1,
                 "on" : 1, "on_str" : "on",
                 "mode" : "fast", "fast" : 1, "instant" : 0}
        assert data == right

        data = mdev.template_data(is_on=False, button=2)
        right = {"address" : addr.hex, "name" : name, "button" : 2,
                 "on" : 0, "on_str" : "off",
                 "mode" : "normal", "fast" : 0, "instant" : 0}
        assert data == right

    #-----------------------------------------------------------------------
    def test_mqtt(self, setup):
        mdev, dev, link = setup.getAll(['mdev', 'dev', 'link'])
        topic = "insteon/%s" % setup.addr.hex

        # Should do nothing
        mdev.load_config({})

        # Send an on/off signal
        dev.signal_on_off.emit(dev, 1, True)
        dev.signal_on_off.emit(dev, 2, False)
        assert len(link.client.pub) == 2
        assert link.client.pub[0] == dict(
            topic='%s/state/1' % topic, payload='on', qos=0, retain=True)
        assert link.client.pub[1] == dict(
            topic='%s/state/2' % topic, payload='off', qos=0, retain=True)
        link.client.clear()

    #-----------------------------------------------------------------------
    def test_config(self, setup):
        mdev, dev, link = setup.getAll(['mdev', 'dev', 'link'])

        config = {'outlet' : {
            'state_topic' : 'foo/{{address}}/{{button}}',
            'state_payload' : '{{button}} {{on}} {{on_str.upper()}}'}}
        qos = 3
        mdev.load_config(config, qos)

        stopic = "foo/%s" % setup.addr.hex

        # Send an on/off signal
        dev.signal_on_off.emit(dev, 1, True)
        dev.signal_on_off.emit(dev, 2, False)
        assert len(link.client.pub) == 2
        assert link.client.pub[0] == dict(
            topic=stopic + "/1", payload='1 1 ON', qos=qos, retain=True)
        assert link.client.pub[1] == dict(
            topic=stopic + "/2", payload='2 0 OFF', qos=qos, retain=True)
        link.client.clear()

    #-----------------------------------------------------------------------
    def test_input_on_off(self, setup):
        mdev, link, proto = setup.getAll(['mdev', 'link', 'proto'])

        # button in topic
        qos = 2
        config = {'outlet' : {
            'on_off_topic' : 'foo/{{address}}/{{button}}',
            'on_off_payload' : ('{ "cmd" : "{{json.on.lower()}}",'
                                '"mode" : "{{json.mode.lower()}}" }')}}
        mdev.load_config(config, qos=qos)

        mdev.subscribe(link, qos)
        topic1 = link.client.sub[0].topic
        topic2 = link.client.sub[2].topic

        payload = b'{ "on" : "OFF", "mode" : "NORMAL" }'
        link.publish(topic1, payload, qos, retain=False)
        assert len(proto.sent) == 1

        # group 1 = standard, group 2 = extended
        assert proto.sent[0].msg.cmd1 == 0x13
        assert isinstance(proto.sent[0].msg, IM.message.OutStandard)
        proto.clear()

        payload = b'{ "on" : "ON", "mode" : "FAST" }'
        link.publish(topic2, payload, qos, retain=False)
        assert len(proto.sent) == 1

        assert proto.sent[0].msg.cmd1 == 0x12
        assert isinstance(proto.sent[0].msg, IM.message.OutExtended)
        proto.clear()

        # test error payload
        link.publish(topic1, b'asdf', qos, False)

    #-----------------------------------------------------------------------
    def test_input_scene(self, setup):
        mdev, link, proto = setup.getAll(['mdev', 'link', 'proto'])

        qos = 2
        config = {'outlet' : {
            'scene_topic' : 'foo/{{address}}/{{button}}',
            'scene_payload' : ('{ "cmd" : "{{json.on.lower()}}" }')}}
        mdev.load_config(config, qos=qos)

        mdev.subscribe(link, qos)
        topic = link.client.sub[1].topic

        payload = b'{ "on" : "OFF" }'
        link.publish(topic, payload, qos, retain=False)
        assert len(proto.sent) == 1

        assert proto.sent[0].msg.cmd1 == 0x30
        assert proto.sent[0].msg.data[3] == 0x13
        proto.clear()

        payload = b'{ "on" : "ON" }'
        link.publish(topic, payload, qos, retain=False)
        assert len(proto.sent) == 1

        assert proto.sent[0].msg.cmd1 == 0x30
        assert proto.sent[0].msg.data[3] == 0x11
        proto.clear()

        # test error payload
        link.publish(topic, b'asdf', qos, False)


#===========================================================================
