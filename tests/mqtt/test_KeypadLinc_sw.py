#===========================================================================
#
# Tests for: insteont_mqtt/mqtt/KeypadLinc.py
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
    dev = IM.device.KeypadLinc(proto, modem, addr, name, dimmer=False)

    link = IM.network.Mqtt()
    mqttModem = H.mqtt.MockModem()
    mqtt = IM.mqtt.Mqtt(link, mqttModem)
    mdev = IM.mqtt.KeypadLinc(mqtt, dev)

    return H.Data(addr=addr, name=name, dev=dev, mdev=mdev, link=link,
                  proto=proto)


#===========================================================================
class Test_KeypadLinc_sw:
    #-----------------------------------------------------------------------
    def test_pubsub(self, setup):
        mdev, addr, link = setup.getAll(['mdev', 'addr', 'link'])

        mdev.subscribe(link, 2)
        assert len(link.client.sub) == 8 * 2

        for i in range(8):
            topic = "insteon/%s/set/%d" % (addr.hex, i + 1)
            assert link.client.sub[i * 2 + 0] == dict(topic=topic, qos=2)

            topic = "insteon/%s/scene/%d" % (addr.hex, i + 1)
            assert link.client.sub[i * 2 + 1] == dict(topic=topic, qos=2)

        mdev.unsubscribe(link)
        assert len(link.client.unsub) == 8 * 2
        for i in range(8):
            topic = "insteon/%s/set/%d" % (addr.hex, i + 1)
            assert link.client.unsub[i * 2 + 0] == dict(topic=topic)

            topic = "insteon/%s/scene/%d" % (addr.hex, i + 1)
            assert link.client.unsub[i * 2 + 1] == dict(topic=topic)

    #-----------------------------------------------------------------------
    def test_template(self, setup):
        mdev, addr, name = setup.getAll(['mdev', 'addr', 'name'])

        data = mdev.template_data(button=5)
        right = {"address" : addr.hex, "name" : name, "button" : 5}
        assert data == right

        data = mdev.template_data(button=3, level=1,
                                  mode=IM.on_off.Mode.FAST,
                                  manual=IM.on_off.Manual.STOP)
        right = {"address" : addr.hex, "name" : name, "button" : 3,
                 "on" : 1, "on_str" : "on", "reason" : "",
                 "level_255" : 1, "level_100" : 0,
                 "mode" : "fast", "fast" : 1, "instant" : 0,
                 "manual_str" : "stop", "manual" : 0, "manual_openhab" : 1}
        assert data == right

        data = mdev.template_data(button=1, level=0)
        right = {"address" : addr.hex, "name" : name, "button" : 1,
                 "on" : 0, "on_str" : "off", "reason" : "",
                 "level_255" : 0, "level_100" : 0,
                 "mode" : "normal", "fast" : 0, "instant" : 0}
        assert data == right

        data = mdev.template_data(button=2, manual=IM.on_off.Manual.UP)
        right = {"address" : addr.hex, "name" : name, "button" : 2,
                 "reason" : "", "manual_str" : "up", "manual" : 1,
                 "manual_openhab" : 2}
        assert data == right

    #-----------------------------------------------------------------------
    def test_mqtt(self, setup):
        mdev, dev, link = setup.getAll(['mdev', 'dev', 'link'])
        topic = "insteon/%s" % setup.addr.hex

        # Should do nothing
        mdev.load_config({})

        # Send an on/off signal
        dev.signal_level_changed.emit(dev, 1, 255)
        dev.signal_level_changed.emit(dev, 2, 0)
        assert len(link.client.pub) == 2
        assert link.client.pub[0] == dict(
            topic='%s/state/1' % topic, payload='on', qos=0, retain=True)
        assert link.client.pub[1] == dict(
            topic='%s/state/2' % topic, payload='off', qos=0, retain=True)
        link.client.clear()

        # Send a manual mode signal - should do nothing w/ the default config.
        dev.signal_manual.emit(dev, 3, IM.on_off.Manual.DOWN)
        dev.signal_manual.emit(dev, 4, IM.on_off.Manual.STOP)
        assert len(link.client.pub) == 0

    #-----------------------------------------------------------------------
    def test_config(self, setup):
        mdev, dev, link = setup.getAll(['mdev', 'dev', 'link'])

        config = {'keypad_linc' : {
            'btn_state_topic' : 'foo/{{address}}/{{button}}',
            'btn_state_payload' : '{{on}} {{on_str.upper()}}',
            'manual_state_topic' : 'bar/{{address}}/{{button}}',
            'manual_state_payload' : '{{manual}} {{manual_str.upper()}}'}}
        qos = 3
        mdev.load_config(config, qos)

        # Send an on/off signal
        dev.signal_level_changed.emit(dev, 3, 128)
        dev.signal_level_changed.emit(dev, 2, 0)
        assert len(link.client.pub) == 2
        assert link.client.pub[0] == dict(
            topic="foo/%s/3" % setup.addr.hex, payload='1 ON', qos=qos,
            retain=True)
        assert link.client.pub[1] == dict(
            topic="foo/%s/2" % setup.addr.hex, payload='0 OFF', qos=qos,
            retain=True)
        link.client.clear()

        # Send a manual signal
        dev.signal_manual.emit(dev, 5, IM.on_off.Manual.DOWN)
        dev.signal_manual.emit(dev, 4, IM.on_off.Manual.STOP)
        assert len(link.client.pub) == 2
        assert link.client.pub[0] == dict(
            topic="bar/%s/5" % setup.addr.hex, payload='-1 DOWN', qos=qos,
            retain=False)
        assert link.client.pub[1] == dict(
            topic="bar/%s/4" % setup.addr.hex, payload='0 STOP', qos=qos,
            retain=False)
        link.client.clear()

    #-----------------------------------------------------------------------
    def test_input_on_off(self, setup):
        mdev, link, addr, proto = setup.getAll(['mdev', 'link', 'addr',
                                                'proto'])

        qos = 2
        config = {'keypad_linc' : {
            'btn_on_off_topic' : 'foo/{{address}}/{{button}}',
            'btn_on_off_payload' : ('{ "cmd" : "{{json.on.lower()}}",'
                                    '"mode" : "{{json.mode.lower()}}" }')}}
        mdev.load_config(config, qos=qos)

        mdev.subscribe(link, qos)

        payload = b'{ "on" : "OFF", "mode" : "NORMAL" }'
        link.publish("foo/%s/3" % addr.hex, payload, qos, retain=False)
        assert len(proto.sent) == 1

        assert proto.sent[0].msg.cmd1 == 0x2e
        proto.clear()

        payload = b'{ "on" : "ON", "mode" : "FAST" }'
        link.publish("foo/%s/1" % addr.hex, payload, qos, retain=False)
        assert len(proto.sent) == 1

        assert proto.sent[0].msg.cmd1 == 0x12
        proto.clear()

        # test error payload
        link.publish("foo/%s/1" % addr.hex, b'asdf', qos, False)

    #-----------------------------------------------------------------------
    def test_input_scene(self, setup):
        mdev, link, addr, proto = setup.getAll(['mdev', 'link', 'addr',
                                                'proto'])

        qos = 2
        config = {'keypad_linc' : {
            'btn_scene_topic' : 'foo/{{address}}/{{button}}',
            'btn_scene_payload' : ('{ "cmd" : "{{json.on.lower()}}" }')}}
        mdev.load_config(config, qos=qos)

        mdev.subscribe(link, qos)

        payload = b'{ "on" : "OFF" }'
        link.publish("foo/%s/3" % addr.hex, payload, qos, retain=False)
        assert len(proto.sent) == 1

        assert proto.sent[0].msg.cmd1 == 0x30
        assert proto.sent[0].msg.data[3] == 0x13
        proto.clear()

        payload = b'{ "on" : "ON" }'
        link.publish("foo/%s/1" % addr.hex, payload, qos, retain=False)
        assert len(proto.sent) == 1

        assert proto.sent[0].msg.cmd1 == 0x30
        assert proto.sent[0].msg.data[3] == 0x11
        proto.clear()

        # test error payload
        link.publish("foo/%s/3" % addr.hex, b'asdf', qos, False)


#===========================================================================
