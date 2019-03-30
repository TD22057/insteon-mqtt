#===========================================================================
#
# insteon_mqtt/network mocking utilities.
#
#===========================================================================
import insteon_mqtt as IM
from .Data import Data

#===========================================================================
class MockMqtt:
    """Mock insteon_mqtt/network/Mqtt class
    """
    signal_connected = IM.Signal()

    def __init__(self):
        self.pub = []
        self.sub = []

    def publish(self, topic, payload, qos=None, retain=None):
        self.pub.append(Data(topic=topic, payload=payload, qos=qos,
                             retain=retain))

    def subscribe(self, topic, qos, callback):
        self.sub.append(Data(topic=topic, qos=qos, callback=callback))

    def unsubscribe(self, topic, qos, callback):
        self.sub.append(Data(topic=topic, qos=qos, callback=callback))


#===========================================================================
class MockMqttClient:
    """Mock Paho MQTT Client class

    See tests/mqtt/test_BatterySensor.py for an example on how to use this.
    """
    def __init__(self, *args, **kwargs):
        self.ctor = (args, kwargs)
        self.pub = []
        self.sub = []
        self.unsub = []
        self.cb = {}

    def clear(self):
        self.pub = []

    def publish(self, topic, payload, qos=None, retain=None):
        data = Data(topic=topic, payload=payload, qos=qos, retain=retain)
        self.pub.append(data)
        if topic in self.cb:
            self.cb[topic](self, None, data)

    def subscribe(self, topic, qos):
        self.sub.append(Data(topic=topic, qos=qos))

    def unsubscribe(self, topic):
        self.unsub.append(Data(topic=topic))
        self.cb.pop(topic, None)

    def message_callback_add(self, topic, callback):
        self.cb[topic] = callback


#===========================================================================
