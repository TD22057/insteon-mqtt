#===========================================================================
#
# MQTT On/Off outlet device
#
#===========================================================================
import functools
from .. import log
from .. import on_off
from .MsgTemplate import MsgTemplate
from . import util
from .StateTopic import StateTopic

LOG = log.get_logger()


class Outlet(StateTopic):
    """MQTT interface to an Insteon on/off outlet.

    This class connects to a device.Outlet object and converts it's
    output state changes to MQTT messages.  It also subscribes to topics to
    allow input MQTT messages to change the state of the Insteon device.

    Outlets will report their state (1/socket) and can be commanded to turn
    on and off.
    """
    def __init__(self, mqtt, device):
        """Constructor

        Args:
          mqtt (mqtt.Mqtt):  The MQTT main interface.
          device (device.Outlet):  The Insteon object to link to.
        """
        # Setup the Topics
        super().__init__(mqtt, device,
                         state_topic='insteon/{{address}}/state/{{button}}')

        # Input on/off command template.
        self.msg_on_off = MsgTemplate(
            topic='insteon/{{address}}/set/{{button}}',
            payload='{ "cmd" : "{{value.lower()}}" }')

    #-----------------------------------------------------------------------
    def load_config(self, config, qos=None):
        """Load values from a configuration data object.

        Args:
          config (dict:  The configuration dictionary to load from.  The object
                 config is stored in config['outlet'].
          qos (int):  The default quality of service level to use.
        """
        data = config.get("outlet", None)
        if not data:
            return

        # Load the various topics
        self.load_state_data(data, qos)

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
        # Connect input topics for groups 1 and 2 (top and bottom sockets).
        # Create a function that will call the input callback with the right
        # group number set for each socket.
        for group in [1, 2]:
            handler = functools.partial(self._input_on_off, group=group)
            data = self.base_template_data(button=group)

            topic = self.msg_on_off.render_topic(data)
            link.subscribe(topic, qos, handler)

    #-----------------------------------------------------------------------
    def unsubscribe(self, link):
        """Unsubscribe to any MQTT topics the object was subscribed to.

        Args:
          link (network.Mqtt):  The MQTT network client to use.
        """
        for group in [1, 2]:
            data = self.base_template_data(button=group)

            topic = self.msg_on_off.render_topic(data)
            link.unsubscribe(topic)

    #-----------------------------------------------------------------------
    def _input_on_off(self, client, data, message, group):
        """Handle an input on/off change MQTT message.

        This is called when we receive a message on the on/off MQTT topic
        subscription.  Parse the message and pass the command to the Insteon
        device.

        Args:
          client (paho.Client):  The paho mqtt client (self.link).
          data:  Optional user data (unused).
          message:  MQTT message - has attrs: topic, payload, qos, retain.
        """
        LOG.debug("Outlet btn %s message %s %s", group, message.topic,
                  message.payload)

        # Parse the input MQTT message.
        data = self.msg_on_off.to_json(message.payload)
        LOG.info("Outlet input command: %s", data)

        try:
            # Tell the device to update it's state.
            is_on, mode, transition = util.parse_on_off(data)
            if mode == on_off.Mode.RAMP or transition is not None:
                LOG.error("Light ON/OFF at Ramp Rate not supported with "
                          "outlets - ignoring ramp rate.")
            if mode == on_off.Mode.RAMP:  # Not supported
                mode = on_off.Mode.NORMAL
            reason = data.get("reason", "")
            self.device.set(level=is_on, group=group, mode=mode, reason=reason)
        except:
            LOG.error("Invalid Outlet on/off command: %s", data)

    #-----------------------------------------------------------------------
