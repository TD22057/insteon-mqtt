#===========================================================================
#
# Network link to an MQTT client class
#
#===========================================================================
import logging
import paho.mqtt.client as paho
from .Link import Link
from .. import Signal

LOG = logging.getLogger(__name__)

class Mqtt (Link):
    """MQTT client link.

    This class bridges an MQTT client (paho-mqtt library) and the
    network manager.  This class adapts the mqtt package to use the
    network manager class to allow for multiple connections and other
    network activity to occur.  This also supports delayed connecting
    (if the broker is down) and automatic reconnects.

    If an MQTT message arrives, Mqtt.signal_message(Link, Messsage) is
    emitted so the message can be processed.  Message is the paho
    message class with attributes topic, payload, qos, and retain.

    Input fields can be set via the constructor or by loading a
    configuration file (see load_config for details).
    """
    def __init__(self, host="127.0.0.1", port=1883, id=None,
                 reconnect_dt=10):
        """Construct an MQTT client.

        This will not actually connect to the broker until connect()
        is called.

        Args:
          host:    (str) The broker host to connect to.
          port:    (int) Thr broker port to connect to.
          id:      (str) Optional connection ID to send.  If not set,
                   'insteon-mqtt' is used.
          reconnect_dt:  (int) Time in seconds to attempt reconnections if
                         the broker is unavailable.

        """
        self.signal_message = Signal.Signal()    # (MqttLink, Message msg)

        super().__init__()
        self.host = host
        self.port = port
        self.connected = False
        self.id = id if id is not None else "insteon-mqtt"

        # Insure poll is called at least once every 15 seconds so we
        # can send a keep alive message to the server so our
        # connection doesn't get dropped.
        self.time_out = 15

        self._reconnect_dt = reconnect_dt
        self._fd = None

        # Create the MQTT client and set the callbacks to our methods.
        self.client = paho.Client(client_id=self.id, clean_session=False)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

    #-----------------------------------------------------------------------
    def load_config(self, config):
        """Load a configuration dictionary.

        Configuration inputs will override any set in the constructor.

        The input configuration dictionary can contain:
        - broker:    (str) The broker host to connect to.
        - port:      (int) Thr broker port to connect to.
        - username:  (str) Optional user name to log in with.
        - passord:   (str) Optional password to log in with.

        Args:
          config:   (dict) Configuration data to load.
        """
        assert(not self.connected)

        self.host = config['broker']
        self.port = config['port']

        username = config.get('username', None)
        if username is not None:
            password = config.get('password', None)
            self.client.username_pw_set(username, password)

    #-----------------------------------------------------------------------
    def publish(self, topic, payload, qos=0, retain=False):
        """Publish an MQTT message.

        Arg:
          topic:    (str) The topic to publish with.
          payload:  (str/bytes) The payload to send for the message.
          qos:      (int) The MQTT QOS level to use (1, 2, or 3).
          retain:   (bool) True to mark the message as retained.
        """
        self.client.publish(topic, payload, qos, retain)
        self.signal_needs_write.emit(self, True)

        LOG.debug("MQTT publish %s %s qos=%s ret=%s", topic, payload, qos,
                  retain)

    #-----------------------------------------------------------------------
    def subscribe(self, topic, qos=0):
        """Subscribe the client to a topic.

        Args:
          topic:   (str) The topic to subscribe to.
        """
        # Tell the client about it and then notify the manager that we
        # have messages to send.
        self.client.subscribe(topic, qos)
        self.signal_needs_write.emit(self, True)

        LOG.debug("MQTT subscribe %s qos=%s", topic, qos)

    #-----------------------------------------------------------------------
    def unsubscribe(self, topic):
        """Unsubscribe the client from a topic.

        Args:
          topic:   (str) The topic to unsubscribe from.
        """
        # Tell the client about it and then notify the manager that we
        # have messages to send.
        self.client.unsubscribe(topic)
        self.signal_needs_write.emit(self, True)

        LOG.debug("MQTT unsubscribe %s", topic)

    #-----------------------------------------------------------------------
    def fileno(self):
        """Return the file descriptor to watch for this link.

        Returns:
          (int) Returns the descriptor (obj.fileno() usually) to monitor.
        """
        assert(self._fd)
        return self._fd

    #-----------------------------------------------------------------------
    def poll(self, t):
        """Periodic poll callback.

        The manager will call this at recurring intervals in case the
        link needs to do some periodic manual processing.

        MQTT requires this to insure that the keep alive messages are
        sent out at reasonable intervals so this must be called
        roughly every 15-30 seconds.
        """
        # This is required to handle keepalive messages.
        self.client.loop_misc()

    #-----------------------------------------------------------------------
    def retry_connect_dt(self):
        """Return a positive integer (seconds) if the link should reconnect.

        If this returns None, the link will not be reconnected if it
        closes.  Otherwise this is the retry interval in seconds to
        try and reconnect the link by calling connect().
        """
        return self._reconnect_dt

    #-----------------------------------------------------------------------
    def connect(self):
        """Connect the link to the device.

        This will try and connect to the MQTT broker.

        Returns:
          (bool) Returns True if the connection was successful or False it
          it failed.
        """
        try:
            self.client.connect(self.host, self.port, keepalive=60)
            self._fd = self.client.socket().fileno()

            LOG.info("MQTT device opened %s %s", self.host, self.port)
            return True
        except:
            LOG.exception("MQTT connection error to %s %s", self.host,
                          self.port)
            return False

    #-----------------------------------------------------------------------
    def read_from_link(self):
        """Read data from the link.

        This will be called by the manager when there is data
        available on the file descriptor for reading.

        Returns:
           (int) Return -1 if the link should be closed.  Or any other
           integer to indicate success.
        """
        # Tell the MQTT client that it ca read.
        status = self.client.loop_read()

        # If status is zero, everything is ok.  Return 1 to tell the
        # link that reading was successful.
        if status == 0:
            return 1

        # Otherwise tell the link that reading failed and we should be
        # closed.
        return -1

    #-----------------------------------------------------------------------
    def write_to_link(self):
        """Write data from the link.

        This will be called by the manager when the file descriptor
        can be written to.  It will only be called after the link as
        emitted the signal_needs_write(True).  Once all the data has
        been written, the link should call
        self.signal_needs_write.emit(False).
        """
        LOG.debug("MQTT writing")

        # Tell the MQTT client that it can write.
        self.client.loop_write()

        # If there is no more data to write, remove us from the write
        # watching.
        if not self.client.want_write():
            self.signal_needs_write.emit(self, False)

    #-----------------------------------------------------------------------
    def close(self):
        """Close the link.

        The link will call self.signal_closing.emit() after closing.
        """
        LOG.info("MQTT device closing %s %s", self.host, self.port)

        self.client.disconnect()
        self.signal_needs_write.emit(self, True)

    #-----------------------------------------------------------------------
    def _on_connect(self, client, data, flags, result):
        """MQTT connection callback.

        This is called by the MQTT client once the connection has
        occurred.
        """
        if result == 0:
            self.connected = True
        else:
            LOG.error("MQTT connection refused %s %s %s", self.host, self.port,
                      result)

    #-----------------------------------------------------------------------
    def _on_disconnect(self, client, data, result):
        """MQTT disconnection callback.

        This is called by the MQTT client when the connection is droppped.
        """
        LOG.info("MQTT disconnection %s %s", self.host, self.port)

        self.connected = False
        self.signal_closing.emit(self)

    #-----------------------------------------------------------------------
    def _on_message(self, client, data, message):
        """MQTT message sent callback.

        This is called by the MQTT client when a message has been sent.
        """
        LOG.info("MQTT message %s %s", message.topic, message.payload)
        self.signal_message.emit(self, message)

    #-----------------------------------------------------------------------
    def __str__(self):
        return "MQTT %s:%d" % (self.host, self.port)

    #-----------------------------------------------------------------------
