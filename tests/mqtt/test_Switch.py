#===========================================================================
#
# Tests for: insteont_mqtt/mqtt/Switch.py
#
# pylint: disable=redefined-outer-name
#===========================================================================
import time
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
    dev = IM.device.Switch(proto, modem, addr, name)

    link = IM.network.Mqtt()
    mqttModem = H.mqtt.MockModem()
    mqtt = IM.mqtt.Mqtt(link, mqttModem)
    mdev = IM.mqtt.Switch(mqtt, dev)

    return H.Data(addr=addr, name=name, dev=dev, mdev=mdev, link=link,
                        proto=proto)


#===========================================================================
class Test_Switch:
    #-----------------------------------------------------------------------
    def test_pubsub(self, setup):
        mdev, addr, link = setup.getAll(['mdev', 'addr', 'link'])

        mdev.subscribe(link, 2)
        assert len(link.client.sub) == 2
        assert link.client.sub[0] == dict(
            topic='insteon/%s/set' % addr.hex, qos=2)
        assert link.client.sub[1] == dict(
            topic='insteon/%s/scene' % addr.hex, qos=2)

        mdev.unsubscribe(link)
        assert len(link.client.unsub) == 2
        assert link.client.unsub[0] == dict(
            topic='insteon/%s/set' % addr.hex)
        assert link.client.unsub[1] == dict(
            topic='insteon/%s/scene' % addr.hex)

    #-----------------------------------------------------------------------
    def test_template(self, setup):
        mdev, addr, name = setup.getAll(['mdev', 'addr', 'name'])

        data = mdev.base_template_data()
        right = {"address" : addr.hex, "name" : name}
        assert data['timestamp'] - time.time() <= 1
        del data['timestamp']
        assert data == right

        data = mdev.state_template_data(is_on=True, mode=IM.on_off.Mode.FAST,
                                        manual=IM.on_off.Manual.STOP,
                                        reason="something")
        right = {"address" : addr.hex, "name" : name,
                 "on" : 1, "on_str" : "on", "reason" : "something",
                 "mode" : "fast", "fast" : 1, "instant" : 0,
                 "manual_str" : "stop", "manual" : 0, "manual_openhab" : 1}
        del data['timestamp']
        assert data == right

        data = mdev.state_template_data(is_on=False)
        right = {"address" : addr.hex, "name" : name, "reason" : "",
                 "on" : 0, "on_str" : "off",
                 "mode" : "normal", "fast" : 0, "instant" : 0}
        del data['timestamp']
        assert data == right

        data = mdev.state_template_data(manual=IM.on_off.Manual.UP,
                                        reason="foo")
        right = {"address" : addr.hex, "name" : name, "reason" : "foo",
                 "manual_str" : "up", "manual" : 1, "manual_openhab" : 2}
        del data['timestamp']
        assert data == right

    #-----------------------------------------------------------------------
    def test_mqtt(self, setup):
        mdev, dev, link = setup.getAll(['mdev', 'dev', 'link'])
        topic = "insteon/%s" % setup.addr.hex

        # Should do nothing
        mdev.load_config({})

        # Send an on/off signal
        dev.signal_state.emit(dev, is_on=True)
        dev.signal_state.emit(dev, is_on=False)
        assert len(link.client.pub) == 2
        assert link.client.pub[0] == dict(
            topic='%s/state' % topic, payload='on', qos=0, retain=True)
        assert link.client.pub[1] == dict(
            topic='%s/state' % topic, payload='off', qos=0, retain=True)
        link.client.clear()

        # Send a manual mode signal - should do nothing w/ the default config.
        dev.signal_manual.emit(dev, manual=IM.on_off.Manual.DOWN)
        dev.signal_manual.emit(dev, manual=IM.on_off.Manual.STOP)
        assert len(link.client.pub) == 0

    #-----------------------------------------------------------------------
    def test_discovery(self, setup):
        mdev, dev, link = setup.getAll(['mdev', 'dev', 'link'])
        topic = "insteon/%s" % setup.addr.hex

        mdev.load_config({"switch": {"junk": "junk"}})
        assert mdev.default_discovery_cls == "switch"
        assert mdev.rendered_topic_map == {
            'manual_state_topic': None,
            'on_off_topic': 'insteon/01.02.03/set',
            'scene_topic': 'insteon/01.02.03/scene',
            'state_topic': 'insteon/01.02.03/state'
        }
        assert len(mdev.extra_topic_nums) == 0

    #-----------------------------------------------------------------------
    def test_config(self, setup):
        mdev, dev, link = setup.getAll(['mdev', 'dev', 'link'])

        config = {'switch' : {
            'state_topic' : 'foo/{{address}}',
            'state_payload' : '{{on}} {{on_str.upper()}}',
            'manual_state_topic' : 'bar/{{address}}',
            'manual_state_payload' : '{{manual}} {{manual_str.upper()}}'}}
        qos = 3
        mdev.load_config(config, qos)

        stopic = "foo/%s" % setup.addr.hex
        mtopic = "bar/%s" % setup.addr.hex

        # Send an on/off signal
        dev.signal_state.emit(dev, is_on=True)
        dev.signal_state.emit(dev, is_on=False)
        assert len(link.client.pub) == 2
        assert link.client.pub[0] == dict(
            topic=stopic, payload='1 ON', qos=qos, retain=True)
        assert link.client.pub[1] == dict(
            topic=stopic, payload='0 OFF', qos=qos, retain=True)
        link.client.clear()

        # Send a manual signal
        dev.signal_manual.emit(dev, manual=IM.on_off.Manual.DOWN)
        dev.signal_manual.emit(dev, manual=IM.on_off.Manual.STOP)
        assert len(link.client.pub) == 2
        assert link.client.pub[0] == dict(
            topic=mtopic, payload='-1 DOWN', qos=qos, retain=False)
        assert link.client.pub[1] == dict(
            topic=mtopic, payload='0 STOP', qos=qos, retain=False)
        link.client.clear()

    #-----------------------------------------------------------------------
    def test_input_on_off(self, setup):
        mdev, link, proto = setup.getAll(['mdev', 'link', 'proto'])

        qos = 2
        config = {'switch' : {
            'on_off_topic' : 'foo/{{address}}',
            'on_off_payload' : ('{ "cmd" : "{{json.on.lower()}}",'
                                '"mode" : "{{json.mode.lower()}}"}')}}
        mdev.load_config(config, qos=qos)

        mdev.subscribe(link, qos)
        topic = link.client.sub[0].topic

        payload = b'{ "on" : "OFF", "mode" : "NORMAL" }'
        link.publish(topic, payload, qos, retain=False)
        assert len(proto.sent) == 1

        assert proto.sent[0].msg.cmd1 == 0x13
        proto.clear()

        payload = b'{ "on" : "ON", "mode" : "FAST" }'
        link.publish(topic, payload, qos, retain=False)
        assert len(proto.sent) == 1

        assert proto.sent[0].msg.cmd1 == 0x12
        proto.clear()

        # test error payload
        link.publish(topic, b'asdf', qos, False)

    #-----------------------------------------------------------------------
    def test_input_on_off_reason(self, setup):
        mdev, link, proto = setup.getAll(['mdev', 'link', 'proto'])

        qos = 2
        config = {'switch' : {
            'on_off_topic' : 'foo/{{address}}',
            'on_off_payload' : ('{ "cmd" : "{{json.on.lower()}}",'
                                '"mode" : "{{json.mode.lower()}}",'
                                '"reason" : "{{json.reason}}" }')}}
        mdev.load_config(config, qos=qos)

        mdev.subscribe(link, qos)
        topic = link.client.sub[0].topic

        payload = b'{ "on" : "OFF", "mode" : "NORMAL", "reason" : "ABC" }'
        link.publish(topic, payload, qos, retain=False)
        assert len(proto.sent) == 1

        assert proto.sent[0].msg.cmd1 == 0x13
        cb = proto.sent[0].handler.callback
        assert cb.keywords == {"reason" : "ABC"}
        proto.clear()

        payload = b'{ "on" : "ON", "mode" : "FAST", "reason" : "baz" }'
        link.publish(topic, payload, qos, retain=False)
        assert len(proto.sent) == 1

        assert proto.sent[0].msg.cmd1 == 0x12
        cb = proto.sent[0].handler.callback
        assert cb.keywords == {"reason" : "baz"}
        proto.clear()

        # test error payload
        link.publish(topic, b'asdf', qos, False)

    #-----------------------------------------------------------------------
    def test_input_scene(self, setup):
        mdev, link, proto = setup.getAll(['mdev', 'link', 'proto'])

        qos = 2
        config = {'switch' : {
            'scene_topic' : 'foo/{{address}}',
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

    #-----------------------------------------------------------------------
    def test_input_scene_reason(self, setup):
        mdev, link, proto, dev = setup.getAll(['mdev', 'link', 'proto', 'dev'])

        qos = 2
        config = {'switch' : {
            'scene_topic' : 'foo/{{address}}',
            'scene_payload' : ('{ "cmd" : "{{json.on.lower()}}",'
                               '"reason" : "{{json.reason}}"}')}}
        mdev.load_config(config, qos=qos)

        mdev.subscribe(link, qos)
        topic = link.client.sub[1].topic

        payload = b'{ "on" : "OFF", "reason" : "a b c" }'
        link.publish(topic, payload, qos, retain=False)
        assert len(proto.sent) == 1

        assert proto.sent[0].msg.cmd1 == 0x30
        assert proto.sent[0].msg.data[3] == 0x13
        cb = proto.sent[0].handler.on_done
        # Signal a success
        cb(True, "Done", None)
        assert dev.broadcast_reason == "a b c"
        proto.clear()

        payload = b'{ "on" : "ON", "reason" : "zyx" }'
        link.publish(topic, payload, qos, retain=False)
        assert len(proto.sent) == 1

        assert proto.sent[0].msg.cmd1 == 0x30
        assert proto.sent[0].msg.data[3] == 0x11
        cb = proto.sent[0].handler.on_done
        # Signal a success
        cb(True, "Done", None)
        assert dev.broadcast_reason == "zyx"
        proto.clear()


#===========================================================================
