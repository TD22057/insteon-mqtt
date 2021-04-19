#===========================================================================
#
# MQTT dimmer switch device
#
#===========================================================================
from .. import log
from .. import on_off
from .MsgTemplate import MsgTemplate
from . import util
from . import topic

LOG = log.get_logger()


class Dimmer(topic.StateTopic, topic.SceneTopic, topic.ManualTopic,
             topic.SetTopic, topic.DiscoveryTopic):
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

        # This defines the default discovery_class for these devices
        self.class_name = "dimmer"

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
        # The discovery topic needs the full config
        self.load_discovery_data(config, qos)

        data = config.get(self.class_name, None)
        if not data:
            return

        # Load the various topics
        self.load_scene_data(data, qos)
        self.load_state_data(data, qos)
        self.load_manual_data(data, qos)
        self.load_set_data(data, qos)

        # Update the MQTT topics and payloads from the config file.
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
        self.set_subscribe(link, qos)

        # Level changing command messages.
        topic_str = self.msg_level.render_topic(self.base_template_data())
        link.subscribe(topic_str, qos, self._input_set_level)

        self.scene_subscribe(link, qos)

    #-----------------------------------------------------------------------
    def unsubscribe(self, link):
        """Unsubscribe to any MQTT topics the object was subscribed to.

        Args:
          link (network.Mqtt):  The MQTT network client to use.
        """
        self.set_unsubscribe(link)

        topic_str = self.msg_level.render_topic(self.base_template_data())
        link.unsubscribe(topic_str)

        self.scene_unsubscribe(link)

    #-----------------------------------------------------------------------
    def discovery_template_data(self, **kwargs):
        """This extends the template data variables defined in the base class

        Adds in level_topic for dimmers.
        """
        # Set up the variables that can be used in the templates.
        data = super().discovery_template_data(**kwargs)  # pylint:disable=E1101
        data['level_topic'] = self.msg_level.render_topic(data)
        return data

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
            level = '0' if not is_on else data.get('level', None)
            if level is not None:
                level = int(level)
            reason = data.get("reason", "")

            # Tell the device to change its level.
            self.device.set(is_on=is_on, level=level, mode=mode, reason=reason)
        except:
            LOG.exception("Invalid dimmer command: %s", data)

    #-----------------------------------------------------------------------
