#===========================================================================
#
# Tests for: insteont_mqtt/mqtt/Remote.py
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
    dev = IM.device.Remote(proto, modem, addr, name, None, 6)

    link = IM.network.Mqtt()
    mqttModem = H.mqtt.MockModem()
    mqtt = IM.mqtt.Mqtt(link, mqttModem)
    mdev = IM.mqtt.Remote(mqtt, dev)

    return H.Data(addr=addr, name=name, dev=dev, mdev=mdev, link=link,
                        proto=proto)


#===========================================================================
class Test_Remote:
    #-----------------------------------------------------------------------
    def test_pubsub(self, setup):
        mdev, link = setup.getAll(['mdev', 'link'])

        # Remote sensor doesn't subscribe to any topics.
        mdev.subscribe(link, 2)
        assert len(link.client.sub) == 0

        mdev.unsubscribe(link)
        assert len(link.client.unsub) == 0

    #-----------------------------------------------------------------------
    def test_template(self, setup):
        mdev, addr, name = setup.getAll(['mdev', 'addr', 'name'])

        data = mdev.base_template_data(button=3)
        right = {"address" : addr.hex, "name" : name, "button" : 3}
        assert data == right

        data = mdev.state_template_data(button=4, is_on=True,
                                        mode=IM.on_off.Mode.FAST,
                                        manual=IM.on_off.Manual.STOP)
        right = {"address" : addr.hex, "name" : name, "button" : 4,
                 "on" : 1, "on_str" : "on",
                 "mode" : "fast", "fast" : 1, "instant" : 0,
                 "manual_str" : "stop", "manual" : 0, "manual_openhab" : 1,
                 "reason": ''}
        assert data == right

        data = mdev.state_template_data(button=4, is_on=False)
        right = {"address" : addr.hex, "name" : name, "button"  : 4,
                 "on" : 0, "on_str" : "off",
                 "mode" : "normal", "fast" : 0, "instant" : 0,
                 "reason": ''}
        assert data == right

        data = mdev.state_template_data(button=5, manual=IM.on_off.Manual.UP)
        right = {"address" : addr.hex, "name" : name, "button" : 5,
                 "manual_str" : "up", "manual" : 1, "manual_openhab" : 2,
                 "reason": ''}
        assert data == right

    #-----------------------------------------------------------------------
    def test_mqtt(self, setup):
        mdev, dev, link = setup.getAll(['mdev', 'dev', 'link'])
        topic = "insteon/%s" % setup.addr.hex

        # Should do nothing
        mdev.load_config({})

        # Send an on/off signal
        dev.signal_state.emit(dev, button=2, is_on=True)
        dev.signal_state.emit(dev, button=4, is_on=False)
        assert len(link.client.pub) == 2
        assert link.client.pub[0] == dict(
            topic='%s/state/2' % topic, payload='on', qos=0, retain=False)
        assert link.client.pub[1] == dict(
            topic='%s/state/4' % topic, payload='off', qos=0, retain=False)
        link.client.clear()

        # Send a manual mode signal - should do nothing w/ the default config.
        dev.signal_manual.emit(dev, button=1, manual=IM.on_off.Manual.DOWN)
        dev.signal_manual.emit(dev, button=1, manual=IM.on_off.Manual.STOP)
        assert len(link.client.pub) == 0

    #-----------------------------------------------------------------------
    def test_discovery(self, setup):
        mdev, dev, link = setup.getAll(['mdev', 'dev', 'link'])
        topic = "insteon/%s" % setup.addr.hex

        mdev.load_config({"remote": {"junk": "junk"},
                          "battery_sensor" : {"junk": "junk"}})
        assert mdev.default_discovery_cls == "remote"
        assert mdev.rendered_topic_map == {
            'heartbeat_topic': 'insteon/01.02.03/heartbeat',
            'low_battery_topic': 'insteon/01.02.03/battery',
            'manual_state_topic': None,
            'state_topic_1': 'insteon/01.02.03/state/1',
            'state_topic_2': 'insteon/01.02.03/state/2',
            'state_topic_3': 'insteon/01.02.03/state/3',
            'state_topic_4': 'insteon/01.02.03/state/4',
            'state_topic_5': 'insteon/01.02.03/state/5',
            'state_topic_6': 'insteon/01.02.03/state/6',
            'state_topic_7': 'insteon/01.02.03/state/7',
            'state_topic_8': 'insteon/01.02.03/state/8'
        }
        assert len(mdev.extra_topic_nums) == 8

    #-----------------------------------------------------------------------
    def test_config(self, setup):
        mdev, dev, link = setup.getAll(['mdev', 'dev', 'link'])

        config = {'remote' : {
            'state_topic' : 'foo/{{address}}/{{button}}',
            'state_payload' : '{{on}} {{on_str.upper()}}',
            'manual_state_topic' : 'bar/{{address}}/{{button}}',
            'manual_state_payload' : '{{manual}} {{manual_str.upper()}}'}}
        qos = 3
        mdev.load_config(config, qos)

        stopic = "foo/%s" % setup.addr.hex
        mtopic = "bar/%s" % setup.addr.hex

        # Send an on/off signal
        dev.signal_state.emit(dev, button=2, is_on=True)
        dev.signal_state.emit(dev, button=4, is_on=False)
        assert len(link.client.pub) == 2
        assert link.client.pub[0] == dict(
            topic="%s/2" % stopic, payload='1 ON', qos=qos, retain=False)
        assert link.client.pub[1] == dict(
            topic="%s/4" % stopic, payload='0 OFF', qos=qos, retain=False)
        link.client.clear()

        # Send a manual signal
        dev.signal_manual.emit(dev, button=1, manual=IM.on_off.Manual.DOWN)
        dev.signal_manual.emit(dev, button=3, manual=IM.on_off.Manual.STOP)
        assert len(link.client.pub) == 2
        assert link.client.pub[0] == dict(
            topic="%s/1" % mtopic, payload='-1 DOWN', qos=qos, retain=False)
        assert link.client.pub[1] == dict(
            topic="%s/3" % mtopic, payload='0 STOP', qos=qos, retain=False)
        link.client.clear()


    #-----------------------------------------------------------------------
    def test_config_battery(self, setup):
        mdev, dev, link = setup.getAll(['mdev', 'dev', 'link'])

        config = {'remote' : {
            'low_battery_topic' : 'bar/{{address}}',
            'low_battery_payload' : '{{is_low}} {{is_low_str.upper()}}',}}
        qos = 3
        mdev.load_config(config, qos)

        btopic = "bar/%s" % setup.addr.hex

        # Send a low battery signal
        dev.signal_low_battery.emit(dev, False)
        dev.signal_low_battery.emit(dev, True)
        assert len(link.client.pub) == 2
        assert link.client.pub[0] == dict(
            topic=btopic, payload='0 OFF', qos=qos, retain=True)
        assert link.client.pub[1] == dict(
            topic=btopic, payload='1 ON', qos=qos, retain=True)


#===========================================================================
