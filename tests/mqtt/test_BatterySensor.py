#===========================================================================
#
# Tests for: insteont_mqtt/mqtt/BatterySensor.py
#
# pylint: disable=redefined-outer-name
#===========================================================================
import pytest
import insteon_mqtt as IM
import helpers

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
    proto = helpers.MockProtocol()
    modem = helpers.MockModem(tmpdir)
    addr = IM.Address(1, 2, 3)
    name = "device name"
    dev = IM.device.BatterySensor(proto, modem, addr, name)

    link = IM.network.Mqtt()
    mqttModem = helpers.MockMqtt_Modem()
    mqtt = IM.mqtt.Mqtt(link, mqttModem)
    mdev = IM.mqtt.BatterySensor(mqtt, dev)

    return dict(addr=addr, name=name, dev=dev, mdev=mdev, link=link)

#===========================================================================
class Test_BatterySensor:
    #-----------------------------------------------------------------------
    def test_pubsub(self, setup):
        mdev = setup['mdev']
        link = setup['link']

        # Battery sensor doesn't subscribe to any topics.
        mdev.subscribe(link, 2)
        assert len(link.client.sub) == 0

        mdev.unsubscribe(link)
        assert len(link.client.sub) == 0

    #-----------------------------------------------------------------------
    def test_template(self, setup):
        mdev = setup['mdev']
        addr = setup['addr']
        name = setup['name']

        data = mdev.template_data()
        right = {"address" : addr.hex, "name" : name}
        assert data == right

        data = mdev.template_data(is_on=True, is_low=False)
        right = {"address" : addr.hex, "name" : name,
                 "on" : 1, "on_str" : "on",
                 "is_low" : 0, "is_low_str" : "off"}
        assert data == right

    #-----------------------------------------------------------------------
    def test_mqtt(self, setup):
        mdev = setup['mdev']
        dev = setup['dev']
        link = setup['link']

        topic = "insteon/%s" % setup['addr'].hex

        # Should do nothing
        mdev.load_config({})

        # Send an on/off signal
        dev.signal_on_off.emit(dev, True)
        dev.signal_on_off.emit(dev, False)
        assert len(link.client.pub) == 2
        assert link.client.pub[0] == ('%s/state' % topic, 'on', 0, True)
        assert link.client.pub[1] == ('%s/state' % topic, 'off', 0, True)

        link.client.clear()

        # Send a low battery signal
        dev.signal_low_battery.emit(dev, False)
        dev.signal_low_battery.emit(dev, True)
        assert len(link.client.pub) == 2
        assert link.client.pub[0] == \
            ('%s/low_battery' % topic, 'off', 0, True)
        assert link.client.pub[1] == \
            ('%s/low_battery' % topic, 'on', 0, True)

    #-----------------------------------------------------------------------
    def test_config(self, setup):
        mdev = setup['mdev']
        dev = setup['dev']
        link = setup['link']

        config = {'battery_sensor' : {
            'state_topic' : 'foo/{{address}}',
            'state_payload' : '{{on}} {{on_str.upper()}}',
            'low_battery_topic' : 'bar/{{address}}',
            'low_battery_payload' : '{{is_low}} {{is_low_str.upper()}}',
            }}
        qos = 3
        mdev.load_config(config, qos)

        stopic = "foo/%s" % setup['addr'].hex
        btopic = "bar/%s" % setup['addr'].hex

        # Send an on/off signal
        dev.signal_on_off.emit(dev, True)
        dev.signal_on_off.emit(dev, False)
        assert len(link.client.pub) == 2
        assert link.client.pub[0] == (stopic, '1 ON', qos, True)
        assert link.client.pub[1] == (stopic, '0 OFF', qos, True)

        link.client.clear()

        # Send a low battery signal
        dev.signal_low_battery.emit(dev, False)
        dev.signal_low_battery.emit(dev, True)
        assert len(link.client.pub) == 2
        assert link.client.pub[0] == (btopic, '0 OFF', qos, True)
        assert link.client.pub[1] == (btopic, '1 ON', qos, True)

#===========================================================================
