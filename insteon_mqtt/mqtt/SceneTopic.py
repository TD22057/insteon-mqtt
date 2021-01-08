#===========================================================================
#
# MQTT Scene Topic
#
#===========================================================================
from .. import log
from .. import on_off
from .MsgTemplate import MsgTemplate
from . import util

LOG = log.get_logger()


class SceneTopic:
    """MQTT interface to the Scene Topic

    This is an abstract class that provides support for the Scene topic.
    """
    def __init__(self, mqtt, device):
        """Constructor

        Args:
          mqtt (mqtt.Mqtt):  The MQTT main interface.
          device (device):  The Insteon object to link to.
        """
        # Input scene on/off command template.
        self.msg_scene = MsgTemplate(
            topic='insteon/{{address}}/scene',
            payload='{ "cmd" : "{{value.lower()}}" }')

    #-----------------------------------------------------------------------
    def load_config_data(self, data, qos=None):
        """Load values from a configuration data object.

        Args:
          data (dict):  The section of the config dict that applies to this
                        class.
          qos (int):  The default quality of service level to use.
        """
        # Update the MQTT topics and payloads from the config file.
        self.msg_scene.load_config(data, 'scene_topic', 'scene_payload', qos)

    #-----------------------------------------------------------------------
    def template_data(self, level=None, mode=on_off.Mode.NORMAL, manual=None,
                      reason=None):
        raise NotImplementedError

    #-----------------------------------------------------------------------
    def subscribe(self, link, qos):
        """Subscribe to any MQTT topics the object needs.

        Subscriptions are used when the object has things that can be
        commanded to change.

        Args:
          link (network.Mqtt):  The MQTT network client to use.
          qos (int):  The quality of service to use.
        """
        # Scene triggering messages.
        topic = self.msg_scene.render_topic(self.template_data())
        link.subscribe(topic, qos, self._input_scene)

    #-----------------------------------------------------------------------
    def unsubscribe(self, link):
        """Unsubscribe to any MQTT topics the object was subscribed to.

        Args:
          link (network.Mqtt):  The MQTT network client to use.
        """
        topic = self.msg_scene.render_topic(self.template_data())
        link.unsubscribe(topic)

    #-----------------------------------------------------------------------
    def _input_scene(self, client, data, message):
        """Handle an input scene MQTT message.

        This is called when we receive a message on the scene trigger MQTT
        topic subscription.  Parse the message and pass the command to the
        Insteon device.

        Args:
          client (paho.Client):  The paho mqtt client (self.link).
          data:  Optional user data (unused).
          message:  MQTT message - has attrs: topic, payload, qos, retain.
        """
        LOG.debug("SceneTopic message %s %s", message.topic, message.payload)

        # Parse the input MQTT message.
        data = self.msg_scene.to_json(message.payload)
        LOG.info("SceneTopic input command: %s", data)
        try:
            # Scenes don't support modes so don't parse that element.
            is_on = util.parse_on_off(data, have_mode=False)
            group = int(data.get('group', 0x01))
            reason = data.get("reason", "")
            level = data.get("level", None)

            # Tell the device to trigger the scene command.
            self.device.scene(is_on, group, reason, level)
        except:
            LOG.error("Invalid SceneTopic command: %s", data)

    #-----------------------------------------------------------------------
