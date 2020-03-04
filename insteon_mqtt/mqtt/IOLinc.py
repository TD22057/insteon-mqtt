#===========================================================================
#
# MQTT On/Off switch device
#
#===========================================================================
from .. import log
from .MsgTemplate import MsgTemplate
from . import util

LOG = log.get_logger()


class IOLinc:
    """MQTT interface to an Insteon IOLinc device.

    This class connects to a device.IOLinc object and converts it's
    output state changes to MQTT messages.  It also subscribes to topics to
    allow input MQTT messages to change the state of the Insteon device.
    """
    def __init__(self, mqtt, device):
        """Constructor

        Args:
          mqtt (mqtt.Mqtt):  The MQTT main interface.
          device (device.IOLinc):  The Insteon object to link to.
        """
        self.mqtt = mqtt
        self.device = device

        # Output state change reporting template.
        self.msg_state = MsgTemplate(
            topic='insteon/{{address}}/state',
            payload='{"sensor": "{{sensor_on_str.lower()}}",' +
            ' "relay": "{{relay_on_str.lower()}}"}')

        # Output relay state change reporting template.
        self.msg_relay_state = MsgTemplate(
            topic='insteon/{{address}}/relay',
            payload='{{relay_on_str.lower()}}')

        # Output sensor state change reporting template.
        self.msg_sensor_state = MsgTemplate(
            topic='insteon/{{address}}/sensor',
            payload='{{sensor_on_str.lower()}}')

        # Input on/off command template.
        self.msg_on_off = MsgTemplate(
            topic='insteon/{{address}}/set',
            payload='{ "cmd" : "{{value.lower()}}" }')

        device.signal_on_off.connect(self._insteon_on_off)

    #-----------------------------------------------------------------------
    def load_config(self, config, qos=None):
        """Load values from a configuration data object.

        Args:
          config (dict:  The configuration dictionary to load from.  The object
                 config is stored in config['io_linc'].
          qos (int):  The default quality of service level to use.
        """
        data = config.get("io_linc", None)
        if not data:
            return

        self.msg_state.load_config(data, 'state_topic', 'state_payload', qos)
        self.msg_relay_state.load_config(data, 'relay_state_topic',
                                         'relay_state_payload', qos)
        self.msg_sensor_state.load_config(data, 'sensor_state_topic',
                                          'sensor_state_payload', qos)
        self.msg_on_off.load_config(data, 'on_off_topic', 'on_off_payload',
                                    qos)

    #-----------------------------------------------------------------------
    def subscribe(self, link, qos):
        """Subscribe to any MQTT topics the object needs.

        Subscriptions are used when the object has things that can be
        commanded to change.

        Args:
          link (network.Mqtt):  The MQTT network client to use.
          qos (int):  The quality of service to use.
        """
        # On/off command messages.
        topic = self.msg_on_off.render_topic(self.template_data())
        link.subscribe(topic, qos, self._input_on_off)

    #-----------------------------------------------------------------------
    def unsubscribe(self, link):
        """Unsubscribe to any MQTT topics the object was subscribed to.

        Args:
          link (network.Mqtt):  The MQTT network client to use.
        """
        topic = self.msg_on_off.render_topic(self.template_data())
        link.unsubscribe(topic)

    #-----------------------------------------------------------------------
    def template_data(self, sensor_is_on=None, relay_is_on=None):
        """Create the Jinja templating data variables for on/off messages.

        Args:
          is_on (bool):  The on/off state of the switch.  If None, on/off and
                mode attributes are not added to the data.

        Returns:
          dict:  Returns a dict with the variables available for templating.
        """
        # Set up the variables that can be used in the templates.
        data = {
            "address" : self.device.addr.hex,
            "name" : self.device.name if self.device.name
                     else self.device.addr.hex,
            }

        if sensor_is_on is not None:
            data["sensor_on"] = 1 if sensor_is_on else 0
            data["sensor_on_str"] = "on" if sensor_is_on else "off"
        if relay_is_on is not None:
            data["relay_on"] = 1 if relay_is_on else 0
            data["relay_on_str"] = "on" if relay_is_on else "off"

        return data

    #-----------------------------------------------------------------------
    def _insteon_on_off(self, device, sensor_is_on, relay_is_on):
        """Device active on/off callback.

        This is triggered via signal when the Insteon device goes active or
        inactive.  It will publish an MQTT message with the new state.

        Args:
          device (device.IOLinc):   The Insteon device that changed.
          is_on (bool):   True for on, False for off.
        """
        LOG.info("MQTT received active change %s, sensor = %s relay = %s",
                 device.label, sensor_is_on, relay_is_on)

        data = self.template_data(sensor_is_on, relay_is_on)
        self.msg_state.publish(self.mqtt, data)
        self.msg_relay_state.publish(self.mqtt, data)
        self.msg_sensor_state.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
    def _input_on_off(self, client, data, message):
        """Handle an input on/off change MQTT message.

        This is called when we receive a message on the on/off MQTT topic
        subscription.  Parse the message and pass the command to the Insteon
        device.

        Args:
          client (paho.Client):  The paho mqtt client (self.link).
          data:  Optional user data (unused).
          message:  MQTT message - has attrs: topic, payload, qos, retain.
        """
        LOG.debug("IOLinc message %s %s", message.topic, message.payload)

        # Parse the input MQTT message.
        data = self.msg_on_off.to_json(message.payload)
        LOG.info("IOLinc input command: %s", data)

        try:
            # IOLinc doesn't support modes so don't parse that element.
            is_on = util.parse_on_off(data, have_mode=False)
            self.device.set(is_on)
        except:
            LOG.exception("Invalid IOLinc on/off command: %s", data)

    #-----------------------------------------------------------------------
