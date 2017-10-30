#===========================================================================
#
# Network and serial link management
#
#===========================================================================
import logging
import paho.mqtt.client as paho
from .Link import Link
from .. import sigslot


class Mqtt (Link):
    def __init__(self, host, port=1883, id=None, reconnect_dt=10):
        super().__init__()
        self.host = host
        self.port = port
        self._reconnect_dt = reconnect_dt
        self._fd = None

        self.signal_connected = sigslot.Signal()  # (MqttLink, bool connected)
        self.signal_message = sigslot.Signal()    # (MqttLink, Message msg)

        self.client = paho.Client(client_id=id)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

        self.log = logging.getLogger(__name__)

    #-----------------------------------------------------------------------
    def publish(self, topic, payload, qos=0, retain=False):
        self.client.publish(topic, payload, qos, retain)
        self.signal_needs_write.emit(self, True)

        self.log.debug("MQTT publish", topic, payload, qos, retain)

    #-----------------------------------------------------------------------
    def subscribe(self, topic, qos=0):
        self.client.subscribe(topic, qos)
        self.signal_needs_write.emit(self, True)

        self.log.debug("MQTT subscribe", topic, qos)

    #-----------------------------------------------------------------------
    def unsubscribe(self, topic):
        self.client.unsubscribe(topic)
        self.signal_needs_write.emit(self, True)

        self.log.debug("MQTT unsubscribe", topic)

    #-----------------------------------------------------------------------
    def fileno(self):
        return self._fd

    #-----------------------------------------------------------------------
    def retry_connect_dt(self):
        return self._reconnect_dt

    #-----------------------------------------------------------------------
    def connect(self):
        try:
            self.client.connect(self.host, self.port)
            self._fd = self.client.socket().fileno()

            self.log.info("MQTT device opened", self.host, self.port)
            return True
        except:
            self.log.exception("MQTT connection error to", self.host,
                               self.port)
            return False

    #-----------------------------------------------------------------------
    def read_from_link(self):
        rtn = self.client.loop_read()

        self.log.debug("MQTT reading status", rtn)
        if rtn == 0:
            return 1
        else:
            return -1

    #-----------------------------------------------------------------------
    def write_to_link(self):
        self.client.loop_write()

        self.log.debug("MQTT writing")

        if not self.client.want_write():
            self.signal_needs_write.emit(self, False)

    #-----------------------------------------------------------------------
    def close(self):
        self.log.info("MQTT device closing", self.host, self.port)

        self.client.disconnect()
        self.signal_needs_write.emit(self, True)

    #-----------------------------------------------------------------------
    def _on_connect(self, client, data, flags, result):
        if result == 0:
            self.signal_connected.emit(self, True)
        else:
            self.log.error("MQTT connection refused", self.host, self.port,
                           result)

    #-----------------------------------------------------------------------
    def _on_disconnect(self, client, data, result):
        self.log.info("MQTT disconnection", self.host, self.port)

        self.signal_closing.emit(self)
        self.signal_connected.emit(self, False)

    #-----------------------------------------------------------------------
    def _on_message(self, client, data, message):
        self.log.info("MQTT message", message.topic, message.payload)
        self.signal_message.emit(self, message)

    #-----------------------------------------------------------------------
