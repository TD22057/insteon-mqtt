#===========================================================================
#
# MQTT Scene Topic
#
#===========================================================================
import functools
from .. import log
from .MsgTemplate import MsgTemplate
from . import util
from .BaseTopic import BaseTopic

LOG = log.get_logger()


class SceneTopic(BaseTopic):
    """MQTT interface to the Scene Topic

    This is an abstract class that provides support for the Scene topic.
    """
    def __init__(self, mqtt, device, scene_topic=None, scene_payload=None,
                 **kwargs):
        """Constructor

        """
        super().__init__(mqtt, device, **kwargs)
        # It looks cleaner setting these long strings here rather than in the
        # function declaration
        if scene_topic is None:
            scene_topic = 'insteon/{{address}}/scene'
        if scene_payload is None:
            scene_payload = '{ "cmd" : "{{json.cmd.lower()}}"' \
                            '{% if json.brightness is defined %}' \
                            '  , "level" : {{json.brightness}}' \
                            '{% endif %}' \
                            '}'
        # Input scene on/off command template.
        self.msg_scene = MsgTemplate(
            topic=scene_topic,
            payload=scene_payload)

    #-----------------------------------------------------------------------
    def load_scene_data(self, data, qos=None, topic=None, payload=None):
        """Load values from a configuration data object.

        Args:
          data (dict):  The section of the config dict that applies to this
                        class.
          qos (int):  The default quality of service level to use.
        """
        if topic is None:
            topic = 'scene_topic'
        if payload is None:
            payload = 'scene_payload'
        # Update the MQTT topics and payloads from the config file.
        self.msg_scene.load_config(data, topic, payload, qos)

    #-----------------------------------------------------------------------
    def scene_subscribe(self, link, qos, group=None):
        """Subscribe to any MQTT topics the object needs.

        Subscriptions are used when the object has things that can be
        commanded to change.

        Args:
          link (network.Mqtt):  The MQTT network client to use.
          qos (int):  The quality of service to use.
        """
        # Scene triggering messages.
        if group is not None:
            handler = functools.partial(self._input_scene, group=group)
            topic = self.msg_scene.render_topic(
                self.base_template_data(button=group)
            )
        else:
            handler = self._input_scene
            topic = self.msg_scene.render_topic(self.base_template_data())
        link.subscribe(topic, qos, handler)

    #-----------------------------------------------------------------------
    def scene_unsubscribe(self, link, group=None):
        """Unsubscribe to any MQTT topics the object was subscribed to.

        Args:
          link (network.Mqtt):  The MQTT network client to use.
        """
        if group is not None:
            data = self.base_template_data(button=group)
            topic = self.msg_scene.render_topic(data)
        else:
            topic = self.msg_scene.render_topic(self.base_template_data())
        link.unsubscribe(topic)

    #-----------------------------------------------------------------------
    def _input_scene(self, client, data, message, group=0x01):
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
            group = int(data.get('group', group))
            reason = data.get("reason", None)
            level = data.get("level", None)

            # Tell the device to trigger the scene command.
            self.device.scene(is_on, group, reason, level)
        except:
            LOG.error("Invalid SceneTopic command: %s", data)

    #-----------------------------------------------------------------------
