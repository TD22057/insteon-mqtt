#===========================================================================
#
# Tests for: insteont_mqtt/mqtt/Dimmer.py
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
    dev = IM.device.Dimmer(proto, modem, addr, name)

    link = IM.network.Mqtt()
    mqttModem = H.mqtt.MockModem()
    mqtt = IM.mqtt.Mqtt(link, mqttModem)
    mdev = IM.mqtt.Dimmer(mqtt, dev)

    return H.Data(addr=addr, name=name, dev=dev, mdev=mdev, link=link,
                        proto=proto)


#===========================================================================
class Test_Dimmer:
    #-----------------------------------------------------------------------
    def test_pubsub(self, setup):
        mdev, addr, link = setup.getAll(['mdev', 'addr', 'link'])

        mdev.subscribe(link, 2)
        assert len(link.client.sub) == 3
        assert link.client.sub[0] == dict(
            topic='insteon/%s/set' % addr.hex, qos=2)
        assert link.client.sub[1] == dict(
            topic='insteon/%s/level' % addr.hex, qos=2)
        assert link.client.sub[2] == dict(
            topic='insteon/%s/scene' % addr.hex, qos=2)

        mdev.unsubscribe(link)
        assert len(link.client.unsub) == 3
        assert link.client.unsub[0] == dict(
            topic='insteon/%s/set' % addr.hex)
        assert link.client.unsub[1] == dict(
            topic='insteon/%s/level' % addr.hex)
        assert link.client.unsub[2] == dict(
            topic='insteon/%s/scene' % addr.hex)

    #-----------------------------------------------------------------------
    def test_template(self, setup):
        mdev, addr, name = setup.getAll(['mdev', 'addr', 'name'])

        data = mdev.template_data()
        right = {"address" : addr.hex, "name" : name}
        assert data == right

        data = mdev.template_data(level=0x55, mode=IM.on_off.Mode.FAST,
                                  manual=IM.on_off.Manual.STOP)
        right = {"address" : addr.hex, "name" : name,
                 "on" : 1, "on_str" : "on",
                 "level_255" : 85, "level_100" : 33,
                 "mode" : "fast", "fast" : 1, "instant" : 0,
                 "manual_str" : "stop", "manual" : 0, "manual_openhab" : 1}
        assert data == right

        data = mdev.template_data(level=0x00)
        right = {"address" : addr.hex, "name" : name,
                 "on" : 0, "on_str" : "off",
                 "level_255" : 0, "level_100" : 0,
                 "mode" : "normal", "fast" : 0, "instant" : 0}
        assert data == right

        data = mdev.template_data(manual=IM.on_off.Manual.UP)
        right = {"address" : addr.hex, "name" : name,
                 "manual_str" : "up", "manual" : 1, "manual_openhab" : 2}
        assert data == right

    #-----------------------------------------------------------------------
    def test_mqtt(self, setup):
        mdev, dev, link = setup.getAll(['mdev', 'dev', 'link'])
        topic = "insteon/%s" % setup.addr.hex

        # Should do nothing
        mdev.load_config({})

        # Send a level signal
        dev.signal_level_changed.emit(dev, 0x12)
        dev.signal_level_changed.emit(dev, 0x00)
        assert len(link.client.pub) == 2
        assert link.client.pub[0] == dict(
            topic='%s/state' % topic,
            payload='{ "state" : "on", "brightness" : 18 }',
            qos=0, retain=True)
        assert link.client.pub[1] == dict(
            topic='%s/state' % topic,
            payload='{ "state" : "off", "brightness" : 0 }',
            qos=0, retain=True)
        link.client.clear()

        # Send a manual mode signal - should do nothing w/ the default config.
        dev.signal_manual.emit(dev, IM.on_off.Manual.DOWN)
        dev.signal_manual.emit(dev, IM.on_off.Manual.STOP)
        assert len(link.client.pub) == 0

    #-----------------------------------------------------------------------
    def test_config(self, setup):
        mdev, dev, link = setup.getAll(['mdev', 'dev', 'link'])

        config = {'dimmer' : {
            'state_topic' : 'foo/{{address}}',
            'state_payload' : '{{on}} {{level_255}}',
            'manual_state_topic' : 'bar/{{address}}',
            'manual_state_payload' : '{{manual}} {{manual_str.upper()}}'}}
        qos = 3
        mdev.load_config(config, qos)

        ltopic = "foo/%s" % setup.addr.hex
        mtopic = "bar/%s" % setup.addr.hex

        # Send a level signal
        dev.signal_level_changed.emit(dev, 0xff)
        dev.signal_level_changed.emit(dev, 0x00)
        assert len(link.client.pub) == 2
        assert link.client.pub[0] == dict(
            topic=ltopic, payload='1 255', qos=qos, retain=True)
        assert link.client.pub[1] == dict(
            topic=ltopic, payload='0 0', qos=qos, retain=True)
        link.client.clear()

        # Send a manual signal
        dev.signal_manual.emit(dev, IM.on_off.Manual.DOWN)
        dev.signal_manual.emit(dev, IM.on_off.Manual.STOP)
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
        config = {'dimmer' : {
            'on_off_topic' : 'foo/{{address}}',
            'on_off_payload' : ('{ "cmd" : "{{json.on.lower()}}",'
                                '"mode" : "{{json.mode.lower()}}" }'),
            'level_topic' : 'bar/{{address}}',
            'level_payload' : ('{ "cmd" : "{{json.on.lower()}}",'
                               '"mode" : "{{json.mode.lower()}}",'
                               '"level" : {{json.level}} }')}}
        mdev.load_config(config, qos=qos)

        mdev.subscribe(link, qos)
        otopic = link.client.sub[0].topic
        ltopic = link.client.sub[1].topic

        payload = b'{ "on" : "OFF", "mode" : "NORMAL" }'
        link.publish(otopic, payload, qos, retain=False)
        assert len(proto.sent) == 1

        assert proto.sent[0].msg.cmd1 == 0x13
        proto.clear()

        payload = b'{ "on" : "ON", "mode" : "FAST" }'
        link.publish(otopic, payload, qos, retain=False)
        assert len(proto.sent) == 1

        assert proto.sent[0].msg.cmd1 == 0x12
        assert proto.sent[0].msg.cmd2 == 0xff
        proto.clear()

        payload = b'{ "on" : "OFF", "mode" : "NORMAL", "level" : 0 }'
        link.publish(ltopic, payload, qos, retain=False)
        assert len(proto.sent) == 1

        assert proto.sent[0].msg.cmd1 == 0x13
        assert proto.sent[0].msg.cmd2 == 0x00
        proto.clear()

        payload = b'{ "on" : "ON", "mode" : "FAST", "level" : 67 }'
        link.publish(ltopic, payload, qos, retain=False)
        assert len(proto.sent) == 1

        assert proto.sent[0].msg.cmd1 == 0x12
        assert proto.sent[0].msg.cmd2 == 0x43
        proto.clear()

        # test error payload
        link.publish(otopic, b'asdf', qos, False)
        link.publish(ltopic, b'asdf', qos, False)

    #-----------------------------------------------------------------------
    def test_input_scene(self, setup):
        mdev, link, proto = setup.getAll(['mdev', 'link', 'proto'])

        qos = 2
        config = {'dimmer' : {
            'scene_topic' : 'foo/{{address}}/scene',
            'scene_payload' : ('{ "cmd" : "{{json.on.lower()}}" }')}}
        mdev.load_config(config, qos=qos)

        mdev.subscribe(link, qos)
        topic = link.client.sub[2].topic

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
