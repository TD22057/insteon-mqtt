#===========================================================================
#
# MQTT main interface
#
#===========================================================================
import json
from .. import log
from . import config
from . import util

LOG = log.get_logger()


class Mqtt:
    """Main MQTT interface class.

    This class translates MQTT messages to Insteon commands and
    Insteon commands into MQTT messages.  Low level MQTT is handled by
    the network.Mqtt class which communicates data to this class via
    Signals.  The main Insteon interface is the Modem which is used to
    find devices to send them commands.  The Modem is also used to
    notify us of new Insteon devices and this class connects their
    state change signals to ourselves so we can send messages out when
    the device state changes.

    This class subscribes to the Insteon command and set topics
    defined in the configuration input.  It will publish state changes
    on the Insteon state topic when the devices change state.

    Insteon Set Commands:

      Commands are input commands.  They push state changes from MQTT
      to the Insteon devices so you can change light levels,
      thermostats, etc.

      Topic: {SET_TOPIC}/ADDRESS

        SET_TOPIC is the configuration file input.  Address is the
        Insteon device address (AA.BB.CC) to send the command to.

      Payload: [CMD] or { 'cmd' : 'CMD', 'ARG' : 'VALUE' ... }

        CMD is the command name.  If the command has no arguments, it
        can be passed in as the payload (e.g. 'ON', 'OFF').  If the
        command has arguments, the input is a JSON dictionary with the
        inputs as key/value pairs:
           { 'cmd' : 'ON', 'level' : 128 }

    State Changes:

      State changes are sent out as published MQTT commands whenever
      an Insteon device changes state.

      Topic: {STATE_TOPIC}/ADDRESS

        STATE_TOPIC is the configuration file input.  Address is the
        Insteon device address (AA.BB.CC) that changed.

      Payload:

        The payload depends on the device.

        - For on/off and motion devices, the payload will be 'ON' or 'OFF'.
        - For dimmers,  the payload will be JSON: { 'level' : LEVEL }
        - For smoke bridge, the payload will be JSON:
          { 'condition' : COND } where COND is the 'smoke', 'CO', 'clear'
          (see devices.SmokeBridge for others)

    System Commands:

      System commands are things that update the Insteon/Mqtt system.

      Topic: {CMD_TOPIC}

        CMD_TOPIC is the configuration file input.

      Payload: [CMD]

        CMD is the command name.  Valid commands are:
        - 'reload_all' : Delete all local device databases and re-download
          them from the devices.  This could take a long time.
    """
    def __init__(self, mqtt_link, modem):
        self.modem = modem
        self.modem.signal_new_device.connect(self.handle_new_device)

        self.link = mqtt_link
        self.link.signal_connected.connect(self.handle_connected)

        # Map of Address ID to MQTT device.
        self.devices = {}

        self._cmd_topic = None
        self._qos = 1
        self._retain = True
        self._config = None

    #-----------------------------------------------------------------------
    def load_config(self, data):
        """Load a configuration dictionary.

        This should be the mqtt key in the configuration data.  Key
        inputs are:

        The input configuration dictionary can contain:
        - broker:    (str) The broker host to connect to.
        - port:      (int) Thr broker port to connect to.
        - username:  (str) Optional user name to log in with.
        - passord:   (str) Optional password to log in with.

        - qos:         (int) QOS level to use for sent messages (Default 1).
        - retain:      (bool) Retain sent messages (Default True)
        - state_topic: (str) The MQTT topic prefix to publish Insteon
                       state changes with.
        - set_topic:   (str) The MQTT topic prefix to subscribe to for
                       Insteont device changes.
        - cmd_topic:   (str) The MQTT topic prefix to subscribe to for
                       system commands.

        Args:
          data:   (dict) Configuration data to load.
        """
        # Pass connection data to the MQTT link.
        self.link.load_config(data)

        self._cmd_topic = util.clean_topic(data['cmd_topic'])
        self._qos = data.get('qos', 1)
        self._retain = data.get('retain', True)

        # Save the config for later passing to devices when they are
        # created.
        self._config = data

        # Subscribe to the new topics.
        if self.link.connected:
            self._subscribe()

    #-----------------------------------------------------------------------
    def publish(self, topic, payload, qos=None, retain=None):
        """Publish a message out.

        Args:
          topic:   (str) The MQTT topic to publish with.
          payload: (str) The MQTT payload to send.
          qos:     (int) None to use the class QOS. Otherwise the QOS level
                   to use.
          retain:  (bool) None to use the class retain flag.  Otherwise
                   the retain flag to use.
        """
        qos = self._qos if qos is None else qos
        retain = self._retain if retain is None else retain
        self.link.publish(topic, payload, qos, retain)

    #-----------------------------------------------------------------------
    def close(self):
        """Close the MQTT link.
        """
        self.link.close()

    #-----------------------------------------------------------------------
    def handle_connected(self, link, connected):
        """MQTT (dis)connection callback.

        This is called when the low levle MQTT client connects to the
        broker.  After the connection, we'll subscribe to our topics.

        Args:
          link:      (network.Mqtt) The MQTT network link.
          connected: (bool) True if connected, False if disconnected.
        """
        if connected:
            self._subscribe()

    #-----------------------------------------------------------------------
    def handle_new_device(self, modem, device):
        """New Insteon device callback.

        This is called when the Insteon modem creates a new device
        (from the config file).  We'll connect the device signals to
        our callbacks so we can send out MQTT messages when the device
        changes.

        Args:
          modem:   (Modem) The Insteon modem device.
          device:  (device.Base) The Insteon device that was added.
        """
        mqtt_cls = config.find(device)
        if not mqtt_cls:
            LOG.error("Coding error - can't find MQTT device class for "
                      "Insteon device %s: %s", device.__class__, device)
            return

        # Create the MQTT device class.  This will also link signals
        # from the Insteon device to the MQTT device.
        obj = mqtt_cls(self, device)

        # Set the configuration input data for this device type.
        if self._config:
            obj.load_config(self._config)

        # Save the MQTT device so we can find it again.
        self.devices[device.addr.id] = obj

    #-----------------------------------------------------------------------
    def handle_cmd(self, client, data, message):
        """MQTT command message callback.

        TODO: doc

        This is called when an MQTT message is received.  Check it's
        topic and pass it off to the correct handler.

        Args:
          link:  (network.Link) The MQTT link the message was read from.
          msg:   Paho.mqtt message object.  has attributes topic and pyaload.
        """
        # Extract the device name/address from the topic and use
        # it to find the device object to handle the command.
        device_id = message.topic.topic.split("/")[-1]
        device = self.modem.find(device_id)
        if not device:
            LOG.error("Unknown Insteon device '%s'", device_id)
            return

        # Decode the JSON payload.
        try:
            data = json.loads(message.payload)
        except:
            LOG.exception("Error decoding command payload: %s",
                          message.payload)
            return

        # Find the command string and map it to the method to use
        # on the device.
        cmd = data.pop("cmd", None)
        if not cmd:
            LOG.error("Input command has no 'cmd' key: %s", cmd)
            return

        cmd_func = device.cmd_map.get(cmd, None)
        if not cmd_func:
            LOG.error("Unknown command '%s' for device %s.  Valid commands: "
                      "%s", cmd, device.__class__.__name__,
                      device.cmd_map.keys())
            return

        try:
            # Pass the rest of the command arguments as keywords
            # to the method.
            cmd_func(**cmd)
        except:
            LOG.exception("Error running command %s on device %s", cmd,
                          device_id)

    #-----------------------------------------------------------------------
    def _subscribe(self):
        """Subscribe to the command and set topics.
        """
        if self._cmd_topic:
            self.link.subscribe(self._cmd_topic + "/#", self._qos,
                                self.handle_cmd)

        for device in self.devices.values():
            device.subscribe(self.link, self._qos)

    #-----------------------------------------------------------------------
    def _unsubscribe(self,):
        """Unsubscribe to the command and set topics.
        """
        if self._cmd_topic:
            self.link.unsubscribe(self._cmd_topic + "/#")

        for device in self.devices.values():
            device.unsubscribe(self.link)

    #-----------------------------------------------------------------------
