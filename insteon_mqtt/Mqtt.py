#===========================================================================
#
# MQTT main interface
#
#===========================================================================
import json
import logging
from . import device as Dev

LOG = logging.getLogger(__name__)


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
        self.modem.signal_new_device.connect(self._new_device)

        self.link = mqtt_link
        self.link.signal_connected.connect(self._connected)
        self.link.signal_message.connect(self._message)

        self._cmd_topic = None
        self._set_topic = None
        self._state_topic = None
        self._qos = 1
        self._retain = True

        self.cmds = {
            'reload_all' : self.modem.reload_all,
            }

    #-----------------------------------------------------------------------
    def load_config(self, config):
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
        self.link.load_config(config)

        # Unsubscribe from previous topics if needed.
        if self._cmd_topic and self.link.connected:
            self._unsubscribe()

        self._cmd_topic = self._clean_topic(config['cmd_topic'])
        self._set_topic = self._clean_topic(config['set_topic'])
        self._state_topic = self._clean_topic(config['state_topic'])
        self._qos = config.get('qos', 1)
        self._retain = config.get('retain', True)

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
    def _connected(self, link, connected):
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
    def _new_device(self, modem, device):
        """New Insteon device callback.

        This is called when the Insteon modem creates a new device
        (from the config file).  We'll connect the device signals to
        our callbacks so we can send out MQTT messages when the device
        changes.

        Args:
          modem:   (Modem) The Insteon modem device.
          device:  (device.Base) The Insteon device that was added.
        """
        # TODO: what's the best way to handle this?  Don't want MQTT
        # specific stuff in the insteon devices but it would be nice
        # not to code up special cases for each here either.

        # On/off devices.
        if hasattr(device, "signal_active"):
            device.signal_active.connect(self._active)

        # Dimmer devices.
        elif hasattr(device, "signal_level_changed"):
            LOG.info("MQTT adding level changed device %s '%s'", device.addr,
                     device.name)

            device.signal_level_changed.connect(self._level_changed)

        # Smoke bridge special case.
        elif isinstance(device, Dev.SmokeBridge):
            device.signal_state_change.connect(self._smoke_bridge)

    #-----------------------------------------------------------------------
    def _level_changed(self, device, level):
        """Device level changed callback.

        This is triggered via signal when the Insteon device level
        changes.  It will publish an MQTT message with the new state.

        Args:
          device:  (device.Base) The Insteon device that changed.
          level:   (int) The new device level (0->255).
        """
        LOG.info("MQTT received level change %s '%s' = %#04x",
                 device.addr, device.name, level)

        topic = "%s/%s" % (self._state_topic, device.addr.hex)
        payload = json.dumps({'level' : level})
        self.publish(topic, payload, retain=self._retain)

    #-----------------------------------------------------------------------
    def _active(self, device, is_active):
        """Device active on/off callback.

        This is triggered via signal when the Insteon device goes
        active or inactive.  It will publish an MQTT message with the
        new state.

        Args:
          device:   (device.Base) The Insteon device that changed.
          is_active (bool) True for on, False for off.
        """
        LOG.info("MQTT received active change %s '%s' = %s",
                 device.addr, device.name, is_active)

        topic = "%s/%s" % (self._state_topic, device.addr.hex)
        payload = 'ON' if is_active else 'OFF'
        self.publish(topic, payload, retain=self._retain)

    #-----------------------------------------------------------------------
    def _smoke_bridge(self, device, condition):
        """Smoke bridge state change callback.

        This is triggered via signal when the Insteon smoke bridge
        sends an alert.  It will publish an MQTT message with the
        alert.

        Args:
          device:    (device.Base) The Insteon device that changed.
          condition: (str) The condition string.
        """
        LOG.info("MQTT received smoke bridge alert %s '%s' = %s",
                 device.addr, device.name, condition)

        topic = "%s/%s" % (self._state_topic, device.addr.hex)
        payload = json.dumps({'condition' : condition})
        self.publish(topic, payload, retain=self._retain)

    #-----------------------------------------------------------------------
    def _message(self, link, msg):
        """MQTT inbound message callback.

        This is called when an MQTT message is received.  Check it's
        topic and pass it off to the correct handler.

        Args:
          link:  (network.Link) The MQTT link the message was read from.
          msg:   Paho.mqtt message object.  has attributes topic and pyaload.

        """
        # Commands for Insteon devices
        if msg.topic.startswith(self._set_topic):
            LOG.info("Insteon command: %s %s", msg.topic, msg.payload)
            self._handle_set(msg.topic, msg.payload)

        # System comands:
        if msg.topic.startswith(self._cmd_topic):
            LOG.info("Command read: %s %s", msg.topic, msg.payload)
            self._handle_cmd(msg.topic, msg.payload)

    #-----------------------------------------------------------------------
    def _handle_cmd(self, topic, payload):
        """System command handler.

        This is called to handle inbound MQTT messages for system commands.

        Args:
          topic:    (str) The MQTT topic.
          payload:  (str) The MQTT message payload.
        """
        try:
            cmd = payload.strip()
            args = {}

            # If the input is a JSON payload, decode it and get the
            # command.
            if '{' in cmd:
                args = json.loads(payload)
                cmd = args.pop('cmd')

            # Find the function by name and call it w/ any additional args.
            func = self.cmds.get(cmd, None)
            if func:
                func(**args)
            else:
                LOG.error("Unknown MQTT command: %s %s", topic, payload)
        except:
            LOG.exception("Error running command: %s %s", topic, payload)

    #-----------------------------------------------------------------------
    def _handle_set(self, topic, payload):
        """Set command parser.

        Parse an input command, find the insteon device the command is
        for and pass it the command.

        Args:
          topic:    (str) The MQTT topic.
          payload:  (str) The MQTT message payload.
        """
        try:
            # Device address is the last element of the topic.
            address = topic.split("/")[-1]
            device = self.modem.find(address.strip())
            if not device:
                LOG.error("Unknown device requested: %s", address)
                return

            # If the device isn't JSON, turn it into JSON so we can
            # just parse JSOn data.
            s = payload.decode("utf-8").strip()

            # Single command input.
            if '{' not in s:
                data = {'cmd' : s}

            # JSON dictionary of command and arguments.
            else:
                data = json.loads(payload)

            # Pass everyting to the device for parsing.
            device.run_command(**data)
        except:
            LOG.exception("Error running set command %s %s", topic, payload)

    #-----------------------------------------------------------------------
    def _subscribe(self):
        """Subscribe to the command and set topics.
        """
        if self._cmd_topic:
            self.link.subscribe(self._cmd_topic + "/#", qos=self._qos)

        if self._set_topic:
            self.link.subscribe(self._set_topic + "/#", qos=self._qos)

    #-----------------------------------------------------------------------
    def _unsubscribe(self,):
        """Unsubscribe to the command and set topics.
        """
        if self._cmd_topic:
            self.link.unsubscribe(self._cmd_topic + "/#")

        if self._set_topic:
            self.link.unsubscribe(self._set_topic + "/#")

    #-----------------------------------------------------------------------
    def _clean_topic(self, topic):
        """Clean up input topics

        This removes any trailing '/' characters and strips whitespace
        from the ends.

        Arg:
          topic:  (str) The input topic.

        Returns:
          (str) Returns the cleaned topic.

        """
        if topic.endswith("/"):
            return topic[:-1].strip()

        return topic.strip()

    #-----------------------------------------------------------------------
