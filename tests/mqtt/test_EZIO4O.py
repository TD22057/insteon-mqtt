#===========================================================================
#
# Tests for: insteon_mqtt/mqtt/EZIO4O.py
#
# pylint: disable=redefined-outer-name
#===========================================================================
import pytest
import insteon_mqtt as IM
import helpers as H

# from .. import message as Msg


# NOTE about mocking: Don't mock classes directly being used by the class
# being tested.  If we do that, then we're not testing whether the class
# actually works with the class it depends on.  For example, let's say we're
# testing class A which depends on B and C.  If we mock B and C and then
# later the API's for B and C change, the test will still pass because in the
# test those are fake interfaces.  Part of what the test or A needs to catch
# are changes in classes that A depends on not being updated in A.  So the
# correct test pattern is to always use the actual classes that A depends on
# and mock the classes that those dependencies depend on.


# Create our MQTT object to test as well as the linked Insteon object and a
# mocked MQTT client to publish to.
@pytest.fixture
def setup(mock_paho_mqtt, tmpdir):
    proto = H.main.MockProtocol()
    modem = H.main.MockModem(tmpdir)
    addr = IM.Address(1, 2, 3)
    name = "device name"
    dev = IM.device.EZIO4O(proto, modem, addr, name)

    link = IM.network.Mqtt()
    mqttModem = H.mqtt.MockModem()
    mqtt = IM.mqtt.Mqtt(link, mqttModem)
    mdev = IM.mqtt.EZIO4O(mqtt, dev)

    return H.Data(
        addr=addr, name=name, dev=dev, mdev=mdev, link=link, proto=proto, modem=modem
    )


class MockSceneDevice:
    def __init__(self, addr=None, is_controller=False, group=None, link_data=None):
        self.addr = addr
        self.is_controller = is_controller
        self.group = group
        if link_data:
            self.link_data = link_data
        elif group:
            self.link_data = [0, 0, group]
        else:
            self.link_data = [0, 0, 0]


#===========================================================================
class Test_EZIO4O:
    #-----------------------------------------------------------------------
    def test_pubsub(self, setup):
        mdev, addr, link = setup.getAll(["mdev", "addr", "link"])

        mdev.subscribe(link, 2)
        assert len(link.client.sub) == 8
        assert link.client.sub[0] == dict(topic="insteon/%s/set/1" % addr.hex, qos=2)
        assert link.client.sub[1] == dict(topic="insteon/%s/scene/1" % addr.hex, qos=2)
        assert link.client.sub[2] == dict(topic="insteon/%s/set/2" % addr.hex, qos=2)
        assert link.client.sub[3] == dict(topic="insteon/%s/scene/2" % addr.hex, qos=2)
        assert link.client.sub[4] == dict(topic="insteon/%s/set/3" % addr.hex, qos=2)
        assert link.client.sub[5] == dict(topic="insteon/%s/scene/3" % addr.hex, qos=2)
        assert link.client.sub[6] == dict(topic="insteon/%s/set/4" % addr.hex, qos=2)
        assert link.client.sub[7] == dict(topic="insteon/%s/scene/4" % addr.hex, qos=2)

        mdev.unsubscribe(link)
        assert len(link.client.unsub) == 8
        assert link.client.unsub[0] == dict(topic="insteon/%s/set/1" % addr.hex)
        assert link.client.unsub[1] == dict(topic="insteon/%s/scene/1" % addr.hex)
        assert link.client.unsub[2] == dict(topic="insteon/%s/set/2" % addr.hex)
        assert link.client.unsub[3] == dict(topic="insteon/%s/scene/2" % addr.hex)
        assert link.client.unsub[4] == dict(topic="insteon/%s/set/3" % addr.hex)
        assert link.client.unsub[5] == dict(topic="insteon/%s/scene/3" % addr.hex)
        assert link.client.unsub[6] == dict(topic="insteon/%s/set/4" % addr.hex)
        assert link.client.unsub[7] == dict(topic="insteon/%s/scene/4" % addr.hex)

    #-----------------------------------------------------------------------
    def test_template(self, setup):
        mdev, addr, name = setup.getAll(["mdev", "addr", "name"])

        data = mdev.template_data()
        right = {"address": addr.hex, "name": name}
        assert data == right

        data = mdev.template_data(
            is_on=True, button=1, reason="something", mode=IM.on_off.Mode.FAST
        )
        right = {
            "address": addr.hex,
            "name": name,
            "button": 1,
            "on": 1,
            "on_str": "on",
            "reason": "something",
            "mode": "fast",
            "fast": 1,
            "instant": 0,
        }
        assert data == right

        data = mdev.template_data(is_on=False, button=2)
        right = {
            "address": addr.hex,
            "name": name,
            "button": 2,
            "on": 0,
            "on_str": "off",
            "reason": "",
            "mode": "normal",
            "fast": 0,
            "instant": 0,
        }
        assert data == right

        data = mdev.template_data(is_on=False, button=3)
        right = {
            "address": addr.hex,
            "name": name,
            "button": 3,
            "on": 0,
            "on_str": "off",
            "reason": "",
            "mode": "normal",
            "fast": 0,
            "instant": 0,
        }
        assert data == right

        data = mdev.template_data(is_on=False, button=4)
        right = {
            "address": addr.hex,
            "name": name,
            "button": 4,
            "on": 0,
            "on_str": "off",
            "reason": "",
            "mode": "normal",
            "fast": 0,
            "instant": 0,
        }
        assert data == right

    #-----------------------------------------------------------------------
    def test_mqtt(self, setup):
        mdev, dev, link = setup.getAll(["mdev", "dev", "link"])
        topic = "insteon/%s" % setup.addr.hex

        # Should do nothing
        mdev.load_config({})

        # Send an on/off signal
        dev.signal_on_off.emit(dev, 1, True)
        dev.signal_on_off.emit(dev, 2, False)
        dev.signal_on_off.emit(dev, 3, True)
        dev.signal_on_off.emit(dev, 4, False)
        assert len(link.client.pub) == 4
        assert link.client.pub[0] == dict(
            topic="%s/state/1" % topic, payload="on", qos=0, retain=True
        )
        assert link.client.pub[1] == dict(
            topic="%s/state/2" % topic, payload="off", qos=0, retain=True
        )
        assert link.client.pub[2] == dict(
            topic="%s/state/3" % topic, payload="on", qos=0, retain=True
        )
        assert link.client.pub[3] == dict(
            topic="%s/state/4" % topic, payload="off", qos=0, retain=True
        )
        link.client.clear()

    #-----------------------------------------------------------------------
    def test_config(self, setup):
        mdev, dev, link = setup.getAll(["mdev", "dev", "link"])

        config = {
            "ezio4o": {
                "state_topic": "foo/{{address}}/{{button}}",
                "state_payload": "{{button}} {{on}} {{on_str.upper()}}",
            }
        }
        qos = 3
        mdev.load_config(config, qos)

        stopic = "foo/%s" % setup.addr.hex

        # Send an on/off signal
        dev.signal_on_off.emit(dev, 1, True)
        dev.signal_on_off.emit(dev, 2, False)
        dev.signal_on_off.emit(dev, 3, True)
        dev.signal_on_off.emit(dev, 4, False)
        assert len(link.client.pub) == 4
        assert link.client.pub[0] == dict(
            topic=stopic + "/1", payload="1 1 ON", qos=qos, retain=True
        )
        assert link.client.pub[1] == dict(
            topic=stopic + "/2", payload="2 0 OFF", qos=qos, retain=True
        )
        assert link.client.pub[2] == dict(
            topic=stopic + "/3", payload="3 1 ON", qos=qos, retain=True
        )
        assert link.client.pub[3] == dict(
            topic=stopic + "/4", payload="4 0 OFF", qos=qos, retain=True
        )
        link.client.clear()

    #-----------------------------------------------------------------------
    def test_input_on_off(self, setup):
        mdev, link, proto = setup.getAll(["mdev", "link", "proto"])

        # button in topic
        qos = 2
        config = {
            "ezio4o": {
                "on_off_topic": "foo/{{address}}/{{button}}",
                "on_off_payload": (
                    '{ "cmd" : "{{json.on.lower()}}",'
                    '"mode" : "{{json.mode.lower()}}" }'
                ),
            }
        }
        mdev.load_config(config, qos=qos)

        mdev.subscribe(link, qos)

        # for all group standard message
        for i in range(4):
            # turn on
            proto.clear()
            payload = b'{ "on" : "ON", "mode" : "NORMAL" }'
            link.publish(link.client.sub[i * 2].topic, payload, qos, retain=False)
            assert len(proto.sent) == 1
            assert proto.sent[0].msg.cmd1 == 0x45
            assert proto.sent[0].msg.cmd2 == i
            assert isinstance(proto.sent[0].msg, IM.message.OutStandard)

            # turn off
            proto.clear()
            payload = b'{ "on" : "OFF", "mode" : "FAST" }'
            link.publish(link.client.sub[i * 2].topic, payload, qos, retain=False)
            assert len(proto.sent) == 1
            assert proto.sent[0].msg.cmd1 == 0x46
            assert proto.sent[0].msg.cmd2 == i
            assert isinstance(proto.sent[0].msg, IM.message.OutStandard)

        # test error payload
        link.publish(link.client.sub[0].topic, b"asdf", qos, False)

    #-----------------------------------------------------------------------
    def test_input_on_off_reason(self, setup):
        mdev, link, proto = setup.getAll(["mdev", "link", "proto"])

        # button in topic
        qos = 2
        config = {
            "ezio4o": {
                "on_off_topic": "foo/{{address}}/{{button}}",
                "on_off_payload": (
                    '{ "cmd" : "{{json.on.lower()}}",'
                    '"mode" : "{{json.mode.lower()}}",'
                    '"reason" : "{{json.reason}}" }'
                ),
            }
        }
        mdev.load_config(config, qos=qos)

        mdev.subscribe(link, qos)

        # for all group standard message
        for i in range(4):
            # turn on
            proto.clear()
            payload = b'{ "on" : "ON", "mode" : "FAST", "reason" : "baz" }'
            link.publish(link.client.sub[i * 2].topic, payload, qos, retain=False)
            assert len(proto.sent) == 1
            assert proto.sent[0].msg.cmd1 == 0x45
            assert proto.sent[0].msg.cmd2 == i
            assert isinstance(proto.sent[0].msg, IM.message.OutStandard)
            cb = proto.sent[0].handler.callback
            assert cb.keywords == {"reason": "baz"}

            # turn off
            proto.clear()
            payload = b'{ "on" : "OFF", "mode" : "NORMAL", "reason" : "ABC" }'
            link.publish(link.client.sub[i * 2].topic, payload, qos, retain=False)
            assert len(proto.sent) == 1
            assert proto.sent[0].msg.cmd1 == 0x46
            assert proto.sent[0].msg.cmd2 == i
            assert isinstance(proto.sent[0].msg, IM.message.OutStandard)
            cb = proto.sent[0].handler.callback
            assert cb.keywords == {"reason": "ABC"}

        # test error payload
        link.publish(link.client.sub[0].topic, b"asdf", qos, False)

    #-----------------------------------------------------------------------
    def test_input_scene(self, setup):
        dev, mdev, link, modem = setup.getAll(["dev", "mdev", "link", "modem"])

        qos = 2
        config = {
            "ezio4o": {
                "scene_topic": "foo/{{address}}/{{button}}",
                "scene_payload": ('{ "cmd" : "{{json.on.lower()}}" }'),
            }
        }
        mdev.load_config(config, qos=qos)

        mdev.subscribe(link, qos)

        # add device to the modem database
        modem.add(dev)

        # add device default responder db link with modem
        local = MockSceneDevice(dev.addr, False, 1, [0, 0, 1])
        remote = MockSceneDevice(modem.addr, True, 1, [0, 0, 1])
        dev.db.add_from_config(remote, local)

        # add device scenes responder db links for each group with modem
        # scene/1 to scene/4  -> device responder for modem group 50 to 53
        for i in range(4):
            local.group = i + 1
            local.link_data = [0, 0, i]
            remote.group = 1
            dev.db.add_from_config(remote, local)

            remote.group = i + 50
            dev.db.add_from_config(remote, local)

        # for all group trigger modem ALL-Link Broadcast -> modem scene
        for i in range(4):
            # turn off
            modem.scenes = []
            payload = b'{ "on" : "OFF" }'
            link.publish(link.client.sub[i * 2 + 1].topic, payload, qos, retain=False)
            assert len(modem.scenes) == 1
            assert modem.scenes[0][0] == 0  # is_on
            assert modem.scenes[0][1] == i + 50  # group

            # turn on
            modem.scenes = []
            payload = b'{ "on" : "ON" }'
            link.publish(link.client.sub[i * 2 + 1].topic, payload, qos, retain=False)
            assert modem.scenes[0][0] == 1  # is_on
            assert modem.scenes[0][1] == i + 50  # group

        # test error payload
        link.publish(link.client.sub[1].topic, b"asdf", qos, False)

    #-----------------------------------------------------------------------
    def test_input_scene_reason(self, setup):
        dev, mdev, link, modem = setup.getAll(["dev", "mdev", "link", "modem"])

        qos = 2
        config = {
            "ezio4o": {
                "scene_topic": "foo/{{address}}/{{button}}",
                "scene_payload": (
                    '{ "cmd" : "{{json.on.lower()}}",' '"reason" : "{{json.reason}}"}'
                ),
            }
        }
        mdev.load_config(config, qos=qos)

        mdev.subscribe(link, qos)

        # add device to the modem database
        modem.add(dev)

        # add device default responder db link with modem
        local = MockSceneDevice(dev.addr, False, 1, [0, 0, 1])
        remote = MockSceneDevice(modem.addr, True, 1, [0, 0, 1])
        dev.db.add_from_config(remote, local)

        # add device scenes responder db links for each group with modem
        # scene/1 to scene/4  -> device responder for modem group 50 to 53
        for i in range(4):
            local.group = i + 1
            local.link_data = [0, 0, i]
            remote.group = 1
            dev.db.add_from_config(remote, local)

            remote.group = i + 50
            dev.db.add_from_config(remote, local)

        # for all group trigger modem ALL-Link Broadcast -> modem scene
        for i in range(4):
            # turn off
            modem.scenes = []
            payload = b'{ "on" : "OFF", "reason" : "a b c" }'
            link.publish(link.client.sub[i * 2 + 1].topic, payload, qos, retain=False)
            assert len(modem.scenes) == 1
            assert modem.scenes[0][0] == 0  # is_on
            assert modem.scenes[0][1] == i + 50  # group
            assert modem.scenes[0][2] == "a b c"  # reason

            # turn on
            modem.scenes = []
            payload = b'{ "on" : "ON", "reason" : "zyx" }'
            link.publish(link.client.sub[i * 2 + 1].topic, payload, qos, retain=False)
            assert len(modem.scenes) == 1
            assert modem.scenes[0][0] == 1  # is_on
            assert modem.scenes[0][1] == i + 50  # group
            assert modem.scenes[0][2] == "zyx"  # reason

        # test error payload
        link.publish(link.client.sub[1].topic, b"asdf", qos, False)


#===========================================================================
