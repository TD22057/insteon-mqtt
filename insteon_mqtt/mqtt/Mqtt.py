#===========================================================================
#
# MQTT main interface
#
#===========================================================================
import functools
import json
import logging
from .. import log
from . import config
from .MsgTemplate import MsgTemplate
from .Reply import Reply

LOG = log.get_logger()


class Mqtt:
    """Main MQTT interface class.

    This class translates MQTT messages to Insteon commands and Insteon
    commands into MQTT messages.  Low level MQTT is handled by the
    network.Mqtt class which communicates data to this class via Signals.
    The main Insteon interface is the Modem which is used to find devices to
    send them commands.  The Modem is also used to notify us of new Insteon
    devices and this class connects their state change signals to ourselves
    so we can send messages out when the device state changes.

    This class subscribes to the Insteon command and set topics defined in
    the configuration input.  It will publish state changes on the Insteon
    state topic when the devices change state.

    The exact format of the output topics and payloads is controlled by the
    configuration file and the individual devices.  The input command topics
    and payloads are passed through a jinja template to convert them to a
    format that a device understands.  For message details, see the
    individual devices.

    This class also handles "system commands".  These are not Insteon
    specific states or updates but are commands that the Insteon-Mqtt system
    implements for various things.  The payload for these messages is always
    a json data object that will get passed to the Insteon device for
    handling

    This class also handles the HomeAssistant status topic and triggers the
    devices to publish their discovery entities when necessary.
    """
    def __init__(self, mqtt_link, modem):
        """Constructor

        Args:
          mqtt_link (network.Mqtt):  The network MQTT link to use for
                    communicating with the MQTT broker.
          modem (mqtt.Modem):  The MQTT PLM modem object.
        """
        # Connect a callback for handling when a new device is created in the
        # modem.  We'll use it to create a corresponding MQTT device.
        self.modem = modem
        self.modem.signal_new_device.connect(self.handle_new_device)

        # Callback for when we're connected to the broker so we can subscribe
        # to the various topics we need to monitor.
        self.link = mqtt_link
        self.link.signal_connected.connect(self.handle_connected)

        # Map of Address ID to MQTT device.
        self.devices = {}

        # The command topic template (MstTemplate) to use.
        self._cmd_topic = None

        # Enable discovery service
        self.discovery_enabled = False

        # The HomeAssistant status topic to use.
        self._ha_status_topic = None

        # The device_info_template
        self.device_info_template = {}

        # The availability topic
        self.availability_topic = ""

        # The discovery base topic, None if not enabled
        self.discovery_topic_base = None

        # MQTT message parameters.  These get loaded via the config.
        self.qos = 1
        self.retain = True

        # Loaded config object.
        self._config = None

    #-----------------------------------------------------------------------
    def load_config(self, data):
        """Load a configuration dictionary.

        This should be the mqtt key in the configuration data.  Key inputs
        are:

        The input configuration dictionary can contain:
        - broker:    (str) The broker host to connect to.
        - port:      (int) Thr broker port to connect to.
        - username:  (str) Optional user name to log in with.
        - password:  (str) Optional password to log in with.

        - qos:         (int) QOS level to use for sent messages (Default 1).
        - retain:      (bool) Retain sent messages (Default True)
        - cmd_topic:   (str) The MQTT topic prefix to subscribe to for
                       system commands.

        Args:
          data (dict):  Configuration data to load.
        """
        # Pass connection data to the MQTT link.  This will configure the
        # connection to the broker.
        self.link.load_config(data)

        # Create a template for prcessing messages on the command topic.
        self._cmd_topic = MsgTemplate.clean_topic(data['cmd_topic'])

        if 'availability_topic' in data:
            self.availability_topic = data['availability_topic']

        # Create a template for prcessing HomeAssistant status messages.
        if 'discovery_ha_status' in data:
            self._ha_status_topic = MsgTemplate.clean_topic(
                data['discovery_ha_status']
            )

        # Load the device_info_template if defined this is a variable shared
        # by all devices
        if 'device_info_template' in data:
            self.device_info_template = data['device_info_template']

        # Check to see that discovery_topic_base is set in config
        self.discovery_topic_base = data.get('discovery_topic_base',
                                             "homeassistant")

        # Check if discovery enabled
        self.discovery_enabled = data.get('enable_discovery', False)
        if not self.discovery_enabled:
            LOG.debug("Discovery disabled via config setting.")

        # MQTT message parameters.
        self.qos = data.get('qos', self.qos)
        self.retain = data.get('retain', self.retain)

        # Save the config for later passing to devices when they are created.
        self._config = data

        # Subscribe to the new topics.
        if self.link.connected:
            self._startup()

    #-----------------------------------------------------------------------
    def publish(self, topic, payload, qos=None, retain=None):
        """Publish a message out.

        Args:
          topic (str):  The MQTT topic to publish with.
          payload (str):  The MQTT payload to send.
          qos (int):  None to use the class QOS. Otherwise the QOS level
              to use.
          retain (bool):  None to use the class retain flag.  Otherwise
                 the retain flag to use.
        """
        qos = self.qos if qos is None else qos
        retain = self.retain if retain is None else retain

        # Pass the message to the network link.
        self.link.publish(topic, payload, qos, retain)

    #-----------------------------------------------------------------------
    def close(self):
        """Close the MQTT link.
        """
        self.link.close()

    #-----------------------------------------------------------------------
    def handle_connected(self, link, connected):
        """MQTT (dis)connection callback.

        This is called when the low level MQTT client connects to the broker.
        After the connection, we'll subscribe to our topics.

        The connected arg doesn't actually tell us if the MQTT link is
        connected.  It just tells us that the connect() call has returned
        without error.  The link.connected attribute will be set to True
        when the link is actually connected.

        Args:
          link (network.Mqtt):  The MQTT network link.
          connected (bool):  True if connected, False if disconnected.
        """
        if self.link.connected:
            self._startup()

    #-----------------------------------------------------------------------
    def handle_new_device(self, modem, device):
        """New Insteon device callback.

        This is called when the Insteon modem creates a new device (from the
        config file).  We'll connect the device signals to our callbacks so
        we can send out MQTT messages when the device changes.

        Args:
          modem (Modem):  The Insteon modem device.
          device (device.Base):  The Insteon device that was added.
        """
        # Find the MQTT class type that matches the new insteon device.
        mqtt_cls = config.find(device)
        if not mqtt_cls:
            LOG.error("Coding error - can't find MQTT device class for "
                      "Insteon device %s: %s", device.__class__, device)
            return

        # Create the MQTT device class.  This will also link signals from the
        # Insteon device to the MQTT device.
        obj = mqtt_cls(self, device)

        # Set the configuration input data for this device type.
        if self._config:
            obj.load_config(self._config, self.qos)

        # Save the MQTT device so we can find it again.
        self.devices[device.addr.id] = obj

        # If we are already connected we need to subscribe this device
        # and publish its discovery entities
        if self.link.connected:
            obj.subscribe(self.link, self.qos)
            self._publish_device_discovery(obj)

    #-----------------------------------------------------------------------
    def handle_cmd(self, client, userdata, message):
        """MQTT command message callback.

        This is called when an MQTT message is received.  Check it's topic
        and pass it off to the correct handler.  The command is a json
        dictionary that contains these keys:

        - session: Optional string to identify this command session.  Server
          will publish user interface messages to the session topic for
          communication back to the remote client.

        - cmd: The command dictionary.  This gets passed to the MQTT device
          that corresponds to the Instoen device for decoding.

        Args:
          client (paho.Client):  The paho mqtt client (self.link).
          data:  Optional user data (unused).
          message:  MQTT message - has attrs: topic, payload, qos, retain.
        """
        LOG.info("MQTT message %s %s", message.topic, message.payload)

        # Decode the JSON payload.
        try:
            data = json.loads(message.payload.decode("utf-8"))
        except:
            LOG.exception("Error decoding command payload: %s",
                          message.payload)
            return

        # For commands, we want the ability to send messages back to show
        # what's happening with the command.  We can't just print them
        # because this is a server.  So if the sender puts a 'session' key in
        # the data, we'll publish these user interface messages to that topic
        # so the remote client can get status upates.  Obviously the remote
        # client and this code have to match what they expect the session
        # topic to be.
        end_reply = lambda *x: None
        if "session" in data:
            # Turn the session into a topic.
            reply_topic = "%s/session/%s" % (message.topic,
                                             data.pop("session"))

            # Push the handle_reply callback to the logging object.  This way
            # any call to LOG.UI() will send out a message.  This allows the
            # server code to use the regular logging API to send out UI
            # messages to the remote client with out changing any of the
            # code.
            reply_cb = functools.partial(self.handle_reply, topic=reply_topic)
            LOG.set_ui_callback(reply_cb)

            # end_reply is called when the command is done and passes
            # record=None to indicate the command is finished.
            end_reply = functools.partial(self.handle_reply, None,
                                          topic=reply_topic)

        # Extract the device name/address from the topic and use it to find
        # the device object to handle the command.
        device_id = message.topic.split("/")[-1]
        device = self.modem.find(device_id)
        if not device:
            LOG.error("Unknown Insteon device '%s'", device_id)
            end_reply()
            return

        # Find the command string and map it to the method to use on the
        # device.
        cmd = data.pop("cmd", None)
        if not cmd:
            LOG.error("Input command has no 'cmd' key: %s", cmd)
            end_reply()
            return

        LOG.ui("Commanding %s device %s cmd=%s", device.type(), device.label,
               cmd)

        # Get the command function from the device.
        cmd_func = device.cmd_map.get(cmd, None)
        if not cmd_func:
            LOG.error("Unknown command '%s' for device type %s.  Valid "
                      "commands: %s", cmd, device.type(),
                      device.cmd_map.keys())
            end_reply()
            return

        # Set up a callback to handle when finished.  This will send out the
        # finaly reply to the session topic to insure the remote client knows
        # what happened.
        def on_done(success, msg, data):
            if success:
                LOG.ui(msg)
            else:
                LOG.error(msg)
            end_reply()

        try:
            # Pass the rest of the command arguments as keywords to the
            # method.
            cmd_func(on_done=on_done, **data)
        except:
            LOG.exception("Error running command %s on device %s", cmd,
                          device.label)
            end_reply()

    #-----------------------------------------------------------------------
    def handle_reply(self, record, topic):
        """: Session logging reply.

        This is called by the LOG.ui() function to handling sending status
        messages to the remote client.  The API is defined by the logging
        system.

        If record is None, that indicates the command is done.  We'll remove
        ourselves as a callback on the logging system in that case.

        Args:
          record:  Logging record.  None if the command is finished.
          topic (str):  The session topic to publish the log message to.
        """
        # Command is finished.  Cleanup and send an END reply.
        if record is None:
            LOG.del_ui_callback()
            reply = Reply(Reply.Type.END)

        # Normal reply.  Convert the logging object to a Reply object to send.
        else:
            type = Reply.Type.MESSAGE
            if record.levelno >= logging.ERROR:
                type = Reply.Type.ERROR

            reply = Reply(type, record.msg % record.args)

        # Publish the message to the remote client.
        payload = reply.to_json()
        self.link.publish(topic, payload)

    #-----------------------------------------------------------------------
    def handle_ha_status(self, client, userdata, message):
        """HomeAssistant Status Topic Monitoring

        See https://www.home-assistant.io/docs/mqtt/birth_will/
        This monitors an MQTT topic where HomeAssistant publishes 'online'
        and 'offline' status messages.  When a 'online' message is received
        it signals that HomeAssistant was restarted and requires the
        Discovery Entities to be published againe.  When 'online' is
        received this method will trigger all devices to re-publish their
        Discovery Entities.

        Args:
          client (paho.Client):  The paho mqtt client (self.link).
          data:  Optional user data (unused).
          message:  MQTT message - has attrs: topic, payload, qos, retain.
        """
        LOG.info("MQTT message %s %s", message.topic, message.payload)

        payload = message.payload.decode("utf-8").strip().lower()
        if payload == 'online':
            for device in self.devices.values():
                self._publish_device_discovery(device)
        elif payload != 'offline':
            LOG.warning("Unexpected HomeAssistant status message %s %s",
                        message.topic, message.payload)

    #-----------------------------------------------------------------------
    def _publish_device_discovery(self, device):
        """Trigger a device to publish its discovery entities

        Checks that discovery is enabled and that the device supports
        discovery.

        Args:
          device: the device to send the publish discovery command
        """
        if self.discovery_enabled:
            if (hasattr(device, 'publish_discovery') and
                    callable(device.publish_discovery)):
                device.publish_discovery()

    #-----------------------------------------------------------------------
    def _startup(self):
        """Startup Process When MQTT Broker Comes Online

        This will subscribe to the command topic and tell all the MQTT
        devices to subscribe to their command topics.

        It will also subscribe to the HomeAssistant status topic and trigger
        all devices to publish their discovery entities
        """
        if self._cmd_topic:
            self.link.subscribe(self._cmd_topic + "/+", self.qos,
                                self.handle_cmd)

        if self._ha_status_topic:
            self.link.subscribe(self._ha_status_topic, self.qos,
                                self.handle_ha_status)

        for device in self.devices.values():
            device.subscribe(self.link, self.qos)
            self._publish_device_discovery(device)

    #-----------------------------------------------------------------------
    def _shutdown(self):
        """Unsubscribe to the command and set topics.

        This will unsubscribe from all the topics.
        """
        if self._cmd_topic:
            self.link.unsubscribe(self._cmd_topic + "/+")

        for device in self.devices.values():
            device.unsubscribe(self.link)

    #-----------------------------------------------------------------------

#===========================================================================
