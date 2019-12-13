#===========================================================================
#
# Tests for: insteont_mqtt/mqtt/SmokeBridge.py
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
    dev = IM.device.SmokeBridge(proto, modem, addr, name)

    link = IM.network.Mqtt()
    mqttModem = H.mqtt.MockModem()
    mqtt = IM.mqtt.Mqtt(link, mqttModem)
    mdev = IM.mqtt.SmokeBridge(mqtt, dev)

    return H.Data(addr=addr, name=name, dev=dev, mdev=mdev, link=link,
                        proto=proto)


#===========================================================================
class Test_SmokeBridge:
    #-----------------------------------------------------------------------
    def test_pubsub(self, setup):
        mdev, link = setup.getAll(['mdev', 'link'])

        # SmokeBridge sensor doesn't subscribe to any topics.
        mdev.subscribe(link, 2)
        assert len(link.client.sub) == 0

        mdev.unsubscribe(link)
        assert len(link.client.unsub) == 0

    #-----------------------------------------------------------------------
    def test_template(self, setup):
        mdev, addr, name, dev = setup.getAll(['mdev', 'addr', 'name', 'dev'])

        data = mdev.template_data(dev.Type.CO, True)
        right = {"address" : addr.hex, "name" : name, "type" : 'co',
                 "on" : 1, "on_str" : "on"}
        assert data == right

        data = mdev.template_data(dev.Type.ERROR, False)
        right = {"address" : addr.hex, "name" : name, "type" : 'error',
                 "on" : 0, "on_str" : "off"}
        assert data == right

    #-----------------------------------------------------------------------
    def test_mqtt(self, setup):
        mdev, dev, link = setup.getAll(['mdev', 'dev', 'link'])
        topic = "insteon/%s" % setup.addr.hex

        # Should do nothing
        mdev.load_config({})

        # Send an on/off signal
        dev.signal_on_off.emit(dev, dev.Type.SMOKE, True)
        dev.signal_on_off.emit(dev, dev.Type.CO, False)
        assert len(link.client.pub) == 2
        assert link.client.pub[0] == dict(
            topic='%s/smoke' % topic, payload='on', qos=0, retain=True)
        assert link.client.pub[1] == dict(
            topic='%s/co' % topic, payload='off', qos=0, retain=True)
        link.client.clear()

    #-----------------------------------------------------------------------
    def test_config(self, setup):
        mdev, dev, link = setup.getAll(['mdev', 'dev', 'link'])

        config = {'smoke_bridge' : {
            'smoke_topic' : 'foo/{{address}}',
            'smoke_payload' : '{{type}} {{on}} {{on_str.upper()}}',
            'co_topic' : 'foo/{{address}}',
            'co_payload' : '{{type}} {{on}} {{on_str.upper()}}',
            'battery_topic' : 'foo/{{address}}',
            'battery_payload' : '{{type}} {{on}} {{on_str.upper()}}',
            'error_topic' : 'foo/{{address}}',
            'error_payload' : '{{type}} {{on}} {{on_str.upper()}}'}}
        qos = 3
        mdev.load_config(config, qos)

        stopic = "foo/%s" % setup.addr.hex

        # Send an on/off signal
        dev.signal_on_off.emit(dev, dev.Type.ERROR, True)
        dev.signal_on_off.emit(dev, dev.Type.LOW_BATTERY, False)
        assert len(link.client.pub) == 2
        assert link.client.pub[0] == dict(
            topic=stopic, payload='error 1 ON', qos=qos, retain=True)
        assert link.client.pub[1] == dict(
            topic=stopic, payload='low_battery 0 OFF', qos=qos, retain=True)
        link.client.clear()


#===========================================================================
