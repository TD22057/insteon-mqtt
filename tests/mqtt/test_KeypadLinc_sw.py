#===========================================================================
#
# Tests for: insteont_mqtt/mqtt/KeypadLinc.py
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
    dev = IM.device.KeypadLinc(proto, modem, addr, name)

    link = IM.network.Mqtt()
    mqttModem = H.mqtt.MockModem()
    mqtt = IM.mqtt.Mqtt(link, mqttModem)
    mdev = IM.mqtt.KeypadLinc(mqtt, dev)

    return H.Data(addr=addr, name=name, dev=dev, mdev=mdev, link=link,
                  proto=proto, modem=modem)


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

        data = mdev.base_template_data(button=5)
        right = {"address" : addr.hex, "name" : name, "button" : 5}
        assert data['timestamp'] - time.time() <= 1
        del data['timestamp']
        assert data == right

        data = mdev.state_template_data(button=3, level=1,
                                        mode=IM.on_off.Mode.FAST,
                                        manual=IM.on_off.Manual.STOP)
        right = {"address" : addr.hex, "name" : name, "button" : 3,
                 "on" : 1, "on_str" : "on", "reason" : "",
                 "level_255" : 1, "level_100" : 0,
                 "mode" : "fast", "fast" : 1, "instant" : 0,
                 "manual_str" : "stop", "manual" : 0, "manual_openhab" : 1}
        del data['timestamp']
        assert data == right

        data = mdev.state_template_data(button=1, level=0)
        right = {"address" : addr.hex, "name" : name, "button" : 1,
                 "on" : 0, "on_str" : "off", "reason" : "",
                 "level_255" : 0, "level_100" : 0,
                 "mode" : "normal", "fast" : 0, "instant" : 0}
        del data['timestamp']
        assert data == right

        data = mdev.state_template_data(button=2, manual=IM.on_off.Manual.UP)
        right = {"address" : addr.hex, "name" : name, "button" : 2,
                 "reason" : "", "manual_str" : "up", "manual" : 1,
                 "manual_openhab" : 2}
        del data['timestamp']
        assert data == right

    #-----------------------------------------------------------------------
    def test_mqtt(self, setup):
        mdev, dev, link = setup.getAll(['mdev', 'dev', 'link'])
        topic = "insteon/%s" % setup.addr.hex

        # Should do nothing
        mdev.load_config({})

        # Send an on/off signal
        dev.signal_state.emit(dev, button=1, level=255)
        dev.signal_state.emit(dev, button=2, level=0)
        assert len(link.client.pub) == 2
        assert link.client.pub[0] == dict(
            topic='%s/state/1' % topic, payload='on', qos=0, retain=True)
        assert link.client.pub[1] == dict(
            topic='%s/state/2' % topic, payload='off', qos=0, retain=True)
        link.client.clear()

        # Send a manual mode signal - should do nothing w/ the default config.
        dev.signal_manual.emit(dev, button=3, manual=IM.on_off.Manual.DOWN)
        dev.signal_manual.emit(dev, button=4, manual=IM.on_off.Manual.STOP)
        assert len(link.client.pub) == 0

    #-----------------------------------------------------------------------
    def test_discovery(self, setup):
        mdev, dev, link = setup.getAll(['mdev', 'dev', 'link'])
        topic = "insteon/%s" % setup.addr.hex

        mdev.load_config({"keypad_linc": {"junk": "junk"}})
        assert mdev.default_discovery_cls == "keypad_linc"
        assert mdev.rendered_topic_map == {
            'btn_on_off_topic_1': 'insteon/01.02.03/set/1',
            'btn_on_off_topic_2': 'insteon/01.02.03/set/2',
            'btn_on_off_topic_3': 'insteon/01.02.03/set/3',
            'btn_on_off_topic_4': 'insteon/01.02.03/set/4',
            'btn_on_off_topic_5': 'insteon/01.02.03/set/5',
            'btn_on_off_topic_6': 'insteon/01.02.03/set/6',
            'btn_on_off_topic_7': 'insteon/01.02.03/set/7',
            'btn_on_off_topic_8': 'insteon/01.02.03/set/8',
            'btn_on_off_topic_9': 'insteon/01.02.03/set/9',
            'btn_scene_topic_1': 'insteon/01.02.03/scene/1',
            'btn_scene_topic_2': 'insteon/01.02.03/scene/2',
            'btn_scene_topic_3': 'insteon/01.02.03/scene/3',
            'btn_scene_topic_4': 'insteon/01.02.03/scene/4',
            'btn_scene_topic_5': 'insteon/01.02.03/scene/5',
            'btn_scene_topic_6': 'insteon/01.02.03/scene/6',
            'btn_scene_topic_7': 'insteon/01.02.03/scene/7',
            'btn_scene_topic_8': 'insteon/01.02.03/scene/8',
            'btn_scene_topic_9': 'insteon/01.02.03/scene/9',
            'btn_state_topic_1': 'insteon/01.02.03/state/1',
            'btn_state_topic_2': 'insteon/01.02.03/state/2',
            'btn_state_topic_3': 'insteon/01.02.03/state/3',
            'btn_state_topic_4': 'insteon/01.02.03/state/4',
            'btn_state_topic_5': 'insteon/01.02.03/state/5',
            'btn_state_topic_6': 'insteon/01.02.03/state/6',
            'btn_state_topic_7': 'insteon/01.02.03/state/7',
            'btn_state_topic_8': 'insteon/01.02.03/state/8',
            'btn_state_topic_9': 'insteon/01.02.03/state/9',
            'manual_state_topic': None
        }
        assert len(mdev.extra_topic_nums) == 9

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
        dev.signal_state.emit(dev, button=3, level=128)
        dev.signal_state.emit(dev, button=2, level=0)
        assert len(link.client.pub) == 2
        assert link.client.pub[0] == dict(
            topic="foo/%s/3" % setup.addr.hex, payload='1 ON', qos=qos,
            retain=True)
        assert link.client.pub[1] == dict(
            topic="foo/%s/2" % setup.addr.hex, payload='0 OFF', qos=qos,
            retain=True)
        link.client.clear()

        # Send a manual signal
        dev.signal_manual.emit(dev, button=5, manual=IM.on_off.Manual.DOWN)
        dev.signal_manual.emit(dev, button=4, manual=IM.on_off.Manual.STOP)
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
    def test_input_transition(self, setup):
        mdev, dev, link, proto, modem = setup.getAll(
                ['mdev', 'dev', 'link', 'proto', 'modem'])

        qos = 2
        config = {'keypad_linc' : {
            'btn_state_topic' : 'insteon/{{address}}/state',
            'btn_state_payload' : '{{on}} {{on_str.upper()}}',
            'btn_on_off_topic' : 'insteon/{{address}}/set/{{button}}',
            'btn_on_off_payload' : ('{ "cmd" : "{{json.state.lower()}}"'
                                    '{% if json.fast is defined %}'
                                        ', "fast" : {{json.fast}}'
                                    '{% endif %}'
                                    '{% if json.instant is defined %}'
                                        ', "instant" : {{json.instant}}'
                                    '{% endif %}'
                                    '{% if json.mode is defined %}'
                                        ', "mode" : "{{json.mode.lower()}}"'
                                    '{% endif %}'
                                    '{% if json.transition is defined %}'
                                        ', "transition" : {{json.transition}}'
                                    '{% endif %}'
                                    ' }')}}
        mdev.load_config(config, qos=qos)

        mdev.subscribe(link, qos)
        stopic = "insteon/%s/state" % setup.addr.hex
        otopic = link.client.sub[0].topic

        # -----------------------
        # Confirm that ramp mode / transition values are ignored for switches
        # -----------------------

        # -----------------------
        # Light off in 32 seconds, mode explicitly specified
        payload = b'{ "state" : "OFF", "mode" : "RAMP", "transition" : 32 }'
        link.publish(otopic, payload, qos, retain=False)
        assert len(proto.sent) == 1

        assert proto.sent[0].msg.cmd1 == 0x13
        assert proto.sent[0].msg.cmd2 == 0x00
        proto.clear()

        # Fake an ACK received
        flags = IM.message.Flags(IM.message.Flags.Type.DIRECT_ACK, False)
        ack = IM.message.InpStandard(setup.addr.hex, modem.addr.hex, flags,
                                     0x13, 0x00)
        dev.handle_ack(ack, IM.util.make_callback(None))

        # Check that reported state matches command
        assert len(link.client.pub) == 2
        assert link.client.pub[1] == dict(
            topic=stopic, payload='0 OFF', qos=qos, retain=True)
        link.client.clear()

        # -----------------------
        # Light on (full brightness) in 90 seconds, mode explicitly specified
        payload = b'{ "state" : "ON", "mode" : "RAMP", "transition" : 90 }'
        link.publish(otopic, payload, qos, retain=False)
        assert len(proto.sent) == 1

        assert proto.sent[0].msg.cmd1 == 0x11
        assert proto.sent[0].msg.cmd2 == 0xff
        proto.clear()

        # Fake an ACK received
        flags = IM.message.Flags(IM.message.Flags.Type.DIRECT_ACK, False)
        ack = IM.message.InpStandard(setup.addr.hex, modem.addr.hex, flags,
                                     0x11, 0xff)
        dev.handle_ack(ack, IM.util.make_callback(None))

        # Check that reported state matches command
        assert len(link.client.pub) == 2
        assert link.client.pub[1] == dict(
            topic=stopic, payload='1 ON', qos=qos, retain=True)
        link.client.clear()

        # -----------------------
        # Light off in 500 seconds, mode implied
        payload = b'{ "state" : "OFF", "transition" : 500 }'
        link.publish(otopic, payload, qos, retain=False)
        assert len(proto.sent) == 1

        assert proto.sent[0].msg.cmd1 == 0x13
        assert proto.sent[0].msg.cmd2 == 0x00
        proto.clear()

        # Fake an ACK received
        flags = IM.message.Flags(IM.message.Flags.Type.DIRECT_ACK, False)
        ack = IM.message.InpStandard(setup.addr.hex, modem.addr.hex, flags,
                                     0x13, 0x00)
        dev.handle_ack(ack, IM.util.make_callback(None))

        # Check that reported state matches command
        assert len(link.client.pub) == 2
        assert link.client.pub[1] == dict(
            topic=stopic, payload='0 OFF', qos=qos, retain=True)
        link.client.clear()

        # -----------------------
        # Light on (level 67) in 0.3 seconds, mode implied
        payload = b'{ "state" : "ON", "level" : "67", "transition" : 0.3 }'
        link.publish(otopic, payload, qos, retain=False)
        assert len(proto.sent) == 1

        assert proto.sent[0].msg.cmd1 == 0x11
        assert proto.sent[0].msg.cmd2 == 0xff
        proto.clear()

        # Fake an ACK received
        flags = IM.message.Flags(IM.message.Flags.Type.DIRECT_ACK, False)
        ack = IM.message.InpStandard(setup.addr.hex, modem.addr.hex, flags,
                                     0x11, 0xff)
        dev.handle_ack(ack, IM.util.make_callback(None))

        # Check that reported state matches command
        assert len(link.client.pub) == 2
        assert link.client.pub[1] == dict(
            topic=stopic, payload='1 ON', qos=qos, retain=True)
        link.client.clear()

        # -----------------------
        # Light off, mode explicitly specified, transition omitted (2s implied)
        payload = b'{ "state" : "OFF", "mode" : "RAMP" }'
        link.publish(otopic, payload, qos, retain=False)
        assert len(proto.sent) == 1

        assert proto.sent[0].msg.cmd1 == 0x13
        assert proto.sent[0].msg.cmd2 == 0x00
        proto.clear()

        # Fake an ACK received
        flags = IM.message.Flags(IM.message.Flags.Type.DIRECT_ACK, False)
        ack = IM.message.InpStandard(setup.addr.hex, modem.addr.hex, flags,
                                     0x13, 0x00)
        dev.handle_ack(ack, IM.util.make_callback(None))

        # Check that reported state matches command
        assert len(link.client.pub) == 2
        assert link.client.pub[1] == dict(
            topic=stopic, payload='0 OFF', qos=qos, retain=True)
        link.client.clear()

        # -----------------------
        # Light on, mode explicitly specified, transition omitted (2s implied)
        payload = b'{ "state" : "ON", "mode" : "RAMP" }'
        link.publish(otopic, payload, qos, retain=False)
        assert len(proto.sent) == 1

        assert proto.sent[0].msg.cmd1 == 0x11
        assert proto.sent[0].msg.cmd2 == 0xff
        proto.clear()

        # Fake an ACK received
        flags = IM.message.Flags(IM.message.Flags.Type.DIRECT_ACK, False)
        ack = IM.message.InpStandard(setup.addr.hex, modem.addr.hex, flags,
                                     0x11, 0xff)
        dev.handle_ack(ack, IM.util.make_callback(None))

        # Check that reported state matches command
        assert len(link.client.pub) == 2
        assert link.client.pub[1] == dict(
            topic=stopic, payload='1 ON', qos=qos, retain=True)
        link.client.clear()

        # -----------------------
        # Test that transition is ignored for fast/instant on/off
        # -----------------------

        # -----------------------
        # Light off in 500 seconds, mode explicitly set to FAST
        payload = b'{ "state" : "OFF", "mode" : "FAST", "transition" : 500 }'
        link.publish(otopic, payload, qos, retain=False)
        assert len(proto.sent) == 1

        assert proto.sent[0].msg.cmd1 == 0x14
        assert proto.sent[0].msg.cmd2 == 0x00
        proto.clear()

        # Fake an ACK received
        flags = IM.message.Flags(IM.message.Flags.Type.DIRECT_ACK, False)
        ack = IM.message.InpStandard(setup.addr.hex, modem.addr.hex, flags,
                                     0x14, 0x00)
        dev.handle_ack(ack, IM.util.make_callback(None))

        # Check that reported state matches command
        assert len(link.client.pub) == 2
        assert link.client.pub[1] == dict(
            topic=stopic, payload='0 OFF', qos=qos, retain=True)
        link.client.clear()

        # -----------------------
        # Light on (level 67) in 0.3 seconds, mode explicitly set to INSTANT
        payload = (b'{ "state" : "ON", "level" : "67", "mode" : "INSTANT",'
                   b'"transition" : 0.3 }')
        link.publish(otopic, payload, qos, retain=False)
        assert len(proto.sent) == 1

        assert proto.sent[0].msg.cmd1 == 0x21
        assert proto.sent[0].msg.cmd2 == 0xff
        proto.clear()

        # Fake an ACK received
        flags = IM.message.Flags(IM.message.Flags.Type.DIRECT_ACK, False)
        ack = IM.message.InpStandard(setup.addr.hex, modem.addr.hex, flags,
                                     0x21, 0xff)
        dev.handle_ack(ack, IM.util.make_callback(None))
        # Check that reported state matches command
        assert len(link.client.pub) == 2
        assert link.client.pub[1] == dict(
            topic=stopic, payload='1 ON', qos=qos, retain=True)
        link.client.clear()

        # -----------------------
        # Light off in 500 seconds, mode explicitly set to FAST
        payload = b'{ "state" : "OFF", "fast" : 1, "transition" : 500 }'
        link.publish(otopic, payload, qos, retain=False)
        assert len(proto.sent) == 1

        assert proto.sent[0].msg.cmd1 == 0x14
        assert proto.sent[0].msg.cmd2 == 0x00
        proto.clear()

        # Fake an ACK received
        flags = IM.message.Flags(IM.message.Flags.Type.DIRECT_ACK, False)
        ack = IM.message.InpStandard(setup.addr.hex, modem.addr.hex, flags,
                                     0x14, 0x00)
        dev.handle_ack(ack, IM.util.make_callback(None))

        # Check that reported state matches command
        assert len(link.client.pub) == 2
        assert link.client.pub[1] == dict(
            topic=stopic, payload='0 OFF', qos=qos, retain=True)
        link.client.clear()

        # -----------------------
        # Light on (level 67) in 0.3 seconds, mode explicitly set to INSTANT
        payload = (b'{ "state" : "ON", "level" : "67", "instant" : 1,'
                   b'"transition" : 0.3 }')
        link.publish(otopic, payload, qos, retain=False)
        assert len(proto.sent) == 1

        assert proto.sent[0].msg.cmd1 == 0x21
        assert proto.sent[0].msg.cmd2 == 0xff
        proto.clear()

        # Fake an ACK received
        flags = IM.message.Flags(IM.message.Flags.Type.DIRECT_ACK, False)
        ack = IM.message.InpStandard(setup.addr.hex, modem.addr.hex, flags,
                                     0x21, 0xff)
        dev.handle_ack(ack, IM.util.make_callback(None))
        # Check that reported state matches command
        assert len(link.client.pub) == 2
        assert link.client.pub[1] == dict(
            topic=stopic, payload='1 ON', qos=qos, retain=True)
        link.client.clear()

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
