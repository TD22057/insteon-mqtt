#===========================================================================
#
# Tests for: insteont_mqtt/mqtt/IOLinc.py
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
    dev = IM.device.IOLinc(proto, modem, addr, name)
    dev.modem_scene = 50

    link = IM.network.Mqtt()
    mqttModem = H.mqtt.MockModem()
    mqtt = IM.mqtt.Mqtt(link, mqttModem)
    mdev = IM.mqtt.IOLinc(mqtt, dev)

    return H.Data(addr=addr, name=name, dev=dev, mdev=mdev, link=link,
                        proto=proto, modem=modem)


#===========================================================================
class Test_IOLinc:
    #-----------------------------------------------------------------------
    def test_pubsub(self, setup):
        mdev, addr, link = setup.getAll(['mdev', 'addr', 'link'])

        mdev.subscribe(link, 2)
        assert len(link.client.sub) == 1
        assert link.client.sub[0] == dict(
            topic='insteon/%s/set' % addr.hex, qos=2)

        mdev.unsubscribe(link)
        assert len(link.client.unsub) == 1
        assert link.client.unsub[0] == dict(
            topic='insteon/%s/set' % addr.hex)

    #-----------------------------------------------------------------------
    def test_template(self, setup):
        mdev, addr, name = setup.getAll(['mdev', 'addr', 'name'])

        data = mdev.template_data()
        right = {"address" : addr.hex, "name" : name}
        assert data == right

        data = mdev.template_data(relay_is_on=True, sensor_is_on=True)
        right = {"address" : addr.hex, "name" : name,
                 "relay_on" : 1, "relay_on_str" : "on",
                 "sensor_on" : 1, "sensor_on_str" : "on"}
        assert data == right

        data = mdev.template_data(relay_is_on=False, sensor_is_on=False)
        right = {"address" : addr.hex, "name" : name,
                 "relay_on" : 0, "relay_on_str" : "off",
                 "sensor_on" : 0, "sensor_on_str" : "off"}
        assert data == right

    #-----------------------------------------------------------------------
    def test_mqtt(self, setup):
        mdev, dev, link = setup.getAll(['mdev', 'dev', 'link'])
        topic = "insteon/%s" % setup.addr.hex

        # Should do nothing
        mdev.load_config({})

        # Send an on/off signal
        dev.signal_on_off.emit(dev, True, True)
        dev.signal_on_off.emit(dev, False, False)
        # There are three topics per message state, relay, sensor
        assert len(link.client.pub) == 6
        assert link.client.pub[0] == dict(
            topic='%s/state' % topic,
            payload='{"sensor": "on", "relay": "on"}',
            qos=0, retain=True)
        assert link.client.pub[1] == dict(
            topic='%s/relay' % topic,
            payload='on',
            qos=0, retain=True)
        assert link.client.pub[2] == dict(
            topic='%s/sensor' % topic,
            payload='on',
            qos=0, retain=True)
        assert link.client.pub[3] == dict(
            topic='%s/state' % topic,
            payload='{"sensor": "off", "relay": "off"}',
            qos=0, retain=True)
        assert link.client.pub[4] == dict(
            topic='%s/relay' % topic,
            payload='off',
            qos=0, retain=True)
        assert link.client.pub[5] == dict(
            topic='%s/sensor' % topic,
            payload='off',
            qos=0, retain=True)
        link.client.clear()

    #-----------------------------------------------------------------------
    def test_config(self, setup):
        mdev, dev, link = setup.getAll(['mdev', 'dev', 'link'])

        config = {'io_linc' : {
            'state_topic' : 'foo/{{address}}',
            'state_payload' : '{{relay_on}} {{relay_on_str.upper()}}',
            'relay_state_topic' : 'foo/{{address}}/relay',
            'relay_state_payload' : '{{relay_on}} {{relay_on_str.upper()}}',
            'sensor_state_topic' : 'foo/{{address}}/sensor',
            'sensor_state_payload' : '{{sensor_on}} {{sensor_on_str.upper()}}'
            }}
        qos = 3
        mdev.load_config(config, qos)

        stopic = "foo/%s" % setup.addr.hex

        # Send an on/off signal
        dev.signal_on_off.emit(dev, True, True)
        dev.signal_on_off.emit(dev, False, False)
        assert len(link.client.pub) == 6
        assert link.client.pub[0] == dict(
            topic=stopic, payload='1 ON', qos=qos, retain=True)
        assert link.client.pub[1] == dict(
            topic=stopic + "/relay", payload='1 ON', qos=qos, retain=True)
        assert link.client.pub[2] == dict(
            topic=stopic + "/sensor", payload='1 ON', qos=qos, retain=True)
        assert link.client.pub[3] == dict(
            topic=stopic, payload='0 OFF', qos=qos, retain=True)
        assert link.client.pub[4] == dict(
            topic=stopic + "/relay", payload='0 OFF', qos=qos, retain=True)
        assert link.client.pub[5] == dict(
            topic=stopic + "/sensor", payload='0 OFF', qos=qos, retain=True)
        link.client.clear()

    #-----------------------------------------------------------------------
    def test_input_on_off(self, setup):
        mdev, link, proto, addr = setup.getAll(['mdev', 'link', 'proto',
                                                'addr'])

        qos = 2
        config = {'io_linc' : {
            'on_off_topic' : 'foo/{{address}}',
            'on_off_payload' : '{ "cmd" : "{{json.on.lower()}}" }'}}
        mdev.load_config(config, qos=qos)

        mdev.subscribe(link, qos)
        topic = 'foo/%s' % addr.hex

        payload = b'{ "on" : "OFF" }'
        link.publish(topic, payload, qos, retain=False)
        assert len(proto.sent) == 1

        assert proto.sent[0].msg.cmd1 == 0x13
        proto.clear()

        payload = b'{ "on" : "ON" }'
        link.publish(topic, payload, qos, retain=False)
        assert len(proto.sent) == 1

        assert proto.sent[0].msg.cmd1 == 0x11
        proto.clear()

        # test error payload
        link.publish(topic, b'asdf', qos, False)


#===========================================================================
