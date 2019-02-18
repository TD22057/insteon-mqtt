#===========================================================================
#
# Common code test helpers.  These are common classes used by multiple tests.
#
#===========================================================================
import pytest
import insteon_mqtt as IM

#===========================================================================
# Modem class
class MockModem:
    # Use the 'tmpdir' fixture and pass that to this constructor.
    def __init__(self, save_path):
        self.save_path = str(save_path)


#===========================================================================
# Protocol class
class MockProtocol:
    signal_received = IM.Signal()
    def add_handler(self, handler):
        pass

#===========================================================================
# network/Mqtt class
class MockNetwork_Mqtt:
    signal_connected = IM.Signal()
    def __init__(self):
        self.pub = []
        self.sub = []

    def publish(self, topic, payload, qos=None, retain=None):
        self.pub.append((topic, payload, qos, retain))

    def subscribe(self, topic, qos, callback):
        self.sub.append((topic, qos, callback))

    def unsubscribe(self, topic, qos, callback):
        self.sub.append((topic, qos, callback))


#===========================================================================
# mqtt/Modem
class MockMqtt_Modem:
    signal_new_device = IM.Signal()


#===========================================================================
# network/Mqtt Paho client class
# See mqtt/test_BatterySensor.py for an example on how to use this.
class MockNetwork_MqttClient:
    def __init__(self, *args, **kwargs):
        self.ctor = (args, kwargs)
        self.pub = []
        self.sub = []
        self.unsub = []

    def clear(self):
        self.pub = []

    def publish(self, topic, payload, qos=None, retain=None):
        self.pub.append((topic, payload, qos, retain))

    def subscribe(self, topic, qos):
        self.sub.append((topic, qos))

    def unsubscribe(self, topic):
        self.unsub.append((topic))


#===========================================================================
