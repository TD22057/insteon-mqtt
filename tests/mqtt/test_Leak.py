#===========================================================================
#
# Tests for: insteont_mqtt/mqtt/Leak.py
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
    dev = IM.device.Leak(proto, modem, addr, name)

    link = IM.network.Mqtt()
    mqttModem = H.mqtt.MockModem()
    mqtt = IM.mqtt.Mqtt(link, mqttModem)
    mdev = IM.mqtt.Leak(mqtt, dev)

    return H.Data(addr=addr, name=name, dev=dev, mdev=mdev, link=link)


#===========================================================================
class Test_Leak:
    #-----------------------------------------------------------------------
    def test_pubsub(self, setup):
        mdev, link = setup.getAll(['mdev', 'link'])

        # Leak sensor doesn't subscribe to any topics.
        mdev.subscribe(link, 2)
        assert len(link.client.sub) == 0

        mdev.unsubscribe(link)
        assert len(link.client.sub) == 0

    #-----------------------------------------------------------------------
    def test_template(self, setup):
        mdev, addr, name = setup.getAll(['mdev', 'addr', 'name'])

        data = mdev.template_data()
        right = {"address" : addr.hex, "name" : name}
        assert data == right

        t0 = time.time()
        data = mdev.template_data(is_wet=True, is_heartbeat=True)
        right = {"address" : addr.hex, "name" : name,
                 "is_wet" : 1, "is_wet_str" : "on", "state" : "wet",
                 "is_dry" : 0, "is_dry_str" : "off",
                 "is_heartbeat" : 1, "is_heartbeat_str" : "on"}
        hb = data.pop('heartbeat_time')
        assert data == right
        pytest.approx(t0, hb, 5)

        data = mdev.template_data(is_wet=False)
        right = {"address" : addr.hex, "name" : name,
                 "is_wet" : 0, "is_wet_str" : "off", "state" : "dry",
                 "is_dry" : 1, "is_dry_str" : "on"}
        assert data == right

    #-----------------------------------------------------------------------
    def test_mqtt(self, setup):
        mdev, dev, link = setup.getAll(['mdev', 'dev', 'link'])

        topic = "insteon/%s" % setup.addr.hex

        # Should do nothing
        mdev.load_config({})

        # Send an on/off signal
        dev.signal_wet.emit(dev, True)
        dev.signal_wet.emit(dev, False)
        assert len(link.client.pub) == 2
        assert link.client.pub[0] == dict(
            topic='%s/wet' % topic, payload='on', qos=0, retain=True)
        assert link.client.pub[1] == dict(
            topic='%s/wet' % topic, payload='off', qos=0, retain=True)

        link.client.clear()

        # Send a low battery signal
        t0 = time.time()
        dev.signal_heartbeat.emit(dev, False)
        dev.signal_heartbeat.emit(dev, True)
        assert len(link.client.pub) == 2
        assert link.client.pub[0] == dict(
            topic='%s/heartbeat' % topic, payload='0', qos=0, retain=True)

        m = link.client.pub[1]
        hb = m.payload
        del m['payload']
        assert m == dict(topic='%s/heartbeat' % topic, qos=0, retain=True)
        pytest.approx(t0, hb, 5)

    #-----------------------------------------------------------------------
    def test_config(self, setup):
        mdev, dev, link = setup.getAll(['mdev', 'dev', 'link'])

        config = {'leak' : {
            'wet_dry_topic' : 'foo/{{address}}',
            'wet_dry_payload' : '{{is_wet}} {{is_wet_str.upper()}}',
            'heartbeat_topic' : 'bar/{{address}}',
            'heartbeat_payload' : '{{heartbeat_time}}'}}
        qos = 3
        mdev.load_config(config, qos)

        stopic = "foo/%s" % setup.addr.hex
        htopic = "bar/%s" % setup.addr.hex

        # Send an on/off signal
        dev.signal_wet.emit(dev, True)
        dev.signal_wet.emit(dev, False)
        assert len(link.client.pub) == 2
        assert link.client.pub[0] == dict(
            topic=stopic, payload='1 ON', qos=qos, retain=True)
        assert link.client.pub[1] == dict(
            topic=stopic, payload='0 OFF', qos=qos, retain=True)
        link.client.clear()

        # Send a heartbeawt signal
        t0 = time.time()
        dev.signal_heartbeat.emit(dev, False)
        dev.signal_heartbeat.emit(dev, True)
        assert len(link.client.pub) == 2
        assert link.client.pub[0] == dict(
            topic=htopic, payload='0', qos=qos, retain=True)

        m = link.client.pub[1]
        hb = m.payload
        del m['payload']
        assert m == dict(topic=htopic, qos=qos, retain=True)
        pytest.approx(t0, hb, 5)
        link.client.clear()

#===========================================================================
