#===========================================================================
#
# MQTT dimmer switch device
#
#===========================================================================
from .. import log
from .. import on_off
from .MsgTemplate import MsgTemplate
from . import util
from .SceneTopic import SceneTopic
from .StateTopic import StateTopic
from .ManualTopic import ManualTopic

LOG = log.get_logger()


class Dimmer(StateTopic, SceneTopic, ManualTopic):
    """MQTT interface to an Insteon dimmer switch.

    This class connects to a device.Dimmer object and converts it's output
    state changes to MQTT messages.  It also subscribes to topics to allow
    input MQTT messages to change the state of the Insteon device.

    Dimmers will report their state and brightness (level) and can be
    commanded to turn on and off or on at a specific level (0-255).
    """
    def __init__(self, mqtt, device):
        """Constructor

        Args:
          mqtt (mqtt.Mqtt):  The MQTT main interface.
          device (device.Dimmer):  The Insteon object to link to.
        """
        # Setup the Topics
        super().__init__(mqtt, device,
                         state_payload='{ "state" : "{{on_str.lower()}}", '
                                       '"brightness" : {{level_255}} }')

        # Input on/off command template.
        self.msg_on_off = MsgTemplate(
            topic='insteon/{{address}}/set',
            payload='{ "cmd" : "{{value.lower()}}" }')

        # Input level command template.
        self.msg_level = MsgTemplate(
            topic='insteon/{{address}}/level',
            payload='{ "cmd" : "{{json.state.lower()}}", '
                    '"level" : {{json.brightness}} }')

    #-----------------------------------------------------------------------
    def load_config(self, config, qos=None):
        """Load values from a configuration data object.

        Args:
          config (dict:  The configuration dictionary to load from.  The object
                 config is stored in config['dimmer'].
          qos (int):  The default quality of service level to use.
        """
        data = config.get("dimmer", None)
        if not data:
            return

        # Load the various topics
        self.load_scene_data(data, qos)
        self.load_state_data(data, qos)
        self.load_manual_data(data, qos)

        # Update the MQTT topics and payloads from the config file.
        self.msg_on_off.load_config(data, 'on_off_topic', 'on_off_payload',
                                    qos)
        self.msg_level.load_config(data, 'level_topic', 'level_payload', qos)

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
        topic = self.msg_on_off.render_topic(self.base_template_data())
        link.subscribe(topic, qos, self._input_on_off)

        # Level changing command messages.
        topic = self.msg_level.render_topic(self.base_template_data())
        link.subscribe(topic, qos, self._input_set_level)

        self.scene_subscribe(link, qos)

    #-----------------------------------------------------------------------
    def unsubscribe(self, link):
        """Unsubscribe to any MQTT topics the object was subscribed to.

        Args:
          link (network.Mqtt):  The MQTT network client to use.
        """
        topic = self.msg_on_off.render_topic(self.base_template_data())
        link.unsubscribe(topic)

        topic = self.msg_level.render_topic(self.base_template_data())
        link.unsubscribe(topic)

        self.scene_unsubscribe(link)

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
        LOG.debug("Dimmer message %s %s", message.topic, message.payload)

        # Parse the input MQTT message.
        data = self.msg_on_off.to_json(message.payload)
        LOG.info("Dimmer input command: %s", data)
        try:
            # Tell the device to update its state.
            is_on, mode, transition = util.parse_on_off(data)
            if mode == on_off.Mode.RAMP or transition is not None:
                LOG.error("Light ON/OFF at Ramp Rate not supported with "
                          "dimmers - ignoring ramp rate.")
            if mode == on_off.Mode.RAMP:  # Not supported
                mode = on_off.Mode.NORMAL
            level = 0 if not is_on else None
            reason = data.get("reason", "")
            self.device.set(level=level, mode=mode, reason=reason)
        except:
            LOG.error("Invalid switch on/off command: %s", data)

    #-----------------------------------------------------------------------
    def _input_set_level(self, client, data, message):
        """Handle an input level change MQTT message.

        This is called when we receive a message on the level change MQTT
        topic subscription.  Parse the message and pass the command to the
        Insteon device.

        Args:
          client (paho.Client):  The paho mqtt client (self.link).
          data:  Optional user data (unused).
          message:  MQTT message - has attrs: topic, payload, qos, retain.
        """
        LOG.info("Dimmer message %s %s", message.topic, message.payload)

        data = self.msg_level.to_json(message.payload)
        LOG.info("Dimmer input command: %s", data)
        try:
            is_on, mode, transition = util.parse_on_off(data)
            if mode == on_off.Mode.RAMP or transition is not None:
                LOG.error("Light ON/OFF at Ramp Rate not supported with "
                          "dimmers - ignoring ramp rate.")
            if mode == on_off.Mode.RAMP:  # Not supported
                mode = on_off.Mode.NORMAL
            level = '0' if not is_on else data.get('level')
            if level is not None:
                level = int(level)
            reason = data.get("reason", "")

            # Tell the device to change its level.
            self.device.set(level=level, mode=mode, reason=reason)
        except:
            LOG.error("Invalid dimmer command: %s", data)

    #-----------------------------------------------------------------------
