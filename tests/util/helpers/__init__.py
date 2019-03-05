#===========================================================================
#
# Common code test helpers.  These are common classes used by multiple tests.
#
#===========================================================================
import insteon_mqtt as IM


#===========================================================================
class Data (dict):
    """dict like object with attribute (data.xx) access"""
    def __init__(self, **kwargs):
        self.update(kwargs)

    def getAll(self, attrs):
        return [getattr(self, i) for i in attrs]

    def __getattribute__(self, name):
        if name in self:
            return self[name]
        return dict.__getattribute__(self, name)


#===========================================================================
# Modem class
class MockModem:
    # Use the 'tmpdir' fixture and pass that to this constructor.
    def __init__(self, save_path):
        self.name = "modem"
        self.addr = IM.Address(0x20, 0x30, 0x40)
        self.save_path = str(save_path)
        self.scenes = []

    def scene(self, is_on, group, num_retry=3, on_done=None):
        self.scenes.append((is_on, group))


#===========================================================================
# Protocol class
class MockProtocol:
    def __init__(self):
        self.signal_received = IM.Signal()
        self.sent = []

    def clear(self):
        self.sent = []

    def send(self, msg, handler, priority=None, after=None):
        self.sent.append(dict(msg=msg, handler=handler))

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
        self.pub.append(dict(topic=topic, payload=payload, qos=qos,
                             retain=retain))

    def subscribe(self, topic, qos, callback):
        self.sub.append(dict(topic=topic, qos=qos, callback=callback))

    def unsubscribe(self, topic, qos, callback):
        self.sub.append(dict(topic=topic, qos=qos, callback=callback))


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
        self.cb = {}

    def clear(self):
        self.pub = []

    def publish(self, topic, payload, qos=None, retain=None):
        data = Data(topic=topic, payload=payload, qos=qos, retain=retain)
        self.pub.append(data)
        if topic in self.cb:
            self.cb[topic](self, None, data)

    def subscribe(self, topic, qos):
        self.sub.append(dict(topic=topic, qos=qos))

    def unsubscribe(self, topic):
        self.unsub.append(dict(topic=topic))
        self.cb.pop(topic, None)

    def message_callback_add(self, topic, callback):
        self.cb[topic] = callback

#===========================================================================
