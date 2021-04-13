#===========================================================================
#
# MQTT Set Topic
#
#===========================================================================
import functools
from ... import log
from ..MsgTemplate import MsgTemplate
from .. import util
# from .. import on_off
from .BaseTopic import BaseTopic

LOG = log.get_logger()


class SetTopic(BaseTopic):
    """MQTT interface to the Set Topic

    This is an abstract class that provides support for the set topic.
    """
    def __init__(self, mqtt, device, set_topic=None, set_payload=None,
                 **kwargs):
        """Set Topic Constructor

        Args:
          mqtt (mqtt.Mqtt):  The MQTT main interface.
          device (device):  The Insteon object to link to.
          set_topic (str): The template for the topic
          set_payload (str): The template for the payload
        """
        super().__init__(mqtt, device, **kwargs)
        # It looks cleaner setting these long strings here rather than in the
        # function declaration
        if set_topic is None:
            set_topic = 'insteon/{{address}}/set'
        if set_payload is None:
            set_payload = '{ "cmd" : "{{value.lower()}}" }'
        # Input set on/off command template.
        self.msg_set = MsgTemplate(
            topic=set_topic,
            payload=set_payload)

    #-----------------------------------------------------------------------
    def load_set_data(self, data, qos=None, topic=None, payload=None):
        """Load values from a configuration data object.

        Args:
          data (dict):  The section of the config dict that applies to this
                        class.
          qos (int):  The default quality of service level to use.
        """
        if topic is None:
            topic = 'on_off_topic'
        if payload is None:
            payload = 'on_off_payload'
        # Update the MQTT topics and payloads from the config file.
        self.msg_set.load_config(data, topic, payload, qos)

        # Add ourselves to the list of topics
        self.topics['on_off_topic'] = self.msg_set.render_topic(
            self.base_template_data()
        )

    #-----------------------------------------------------------------------
    def set_subscribe(self, link, qos, group=None):
        """Subscribe to any MQTT topics the object needs.

        Subscriptions are used when the object has things that can be
        commanded to change.

        Args:
          link (network.Mqtt):  The MQTT network client to use.
          qos (int):  The quality of service to use.
        """
        # set triggering messages.
        if group is not None:
            handler = functools.partial(self._input_set, group=group)
        else:
            handler = self._input_set
        topic = self.msg_set.render_topic(
            self.base_template_data(button=group)
        )
        link.subscribe(topic, qos, handler)

    #-----------------------------------------------------------------------
    def set_unsubscribe(self, link, group=None):
        """Unsubscribe to any MQTT topics the object was subscribed to.

        Args:
          link (network.Mqtt):  The MQTT network client to use.
        """
        if group is not None:
            data = self.base_template_data(button=group)
            topic = self.msg_set.render_topic(data)
        else:
            topic = self.msg_set.render_topic(self.base_template_data())
        link.unsubscribe(topic)

    #-----------------------------------------------------------------------
    def _input_set(self, client, data, message, group=0x01):
        """Handle an input set MQTT message.

        This is called when we receive a message on the set trigger MQTT
        topic subscription.  Parse the message and pass the command to the
        Insteon device.

        Args:
          client (paho.Client):  The paho mqtt client (self.link).
          data:  Optional user data (unused).
          message:  MQTT message - has attrs: topic, payload, qos, retain.
        """
        LOG.debug("SetTopic message %s %s", message.topic, message.payload)

        # Parse the input MQTT message.
        data = self.msg_set.to_json(message.payload)
        LOG.info("SetTopic input command: %s", data)
        try:
            # Tell the device to update its state.
            is_on, mode, transition = util.parse_on_off(data)
            level = data.get("level", None)
            reason = data.get("reason", "")
            self.device.set(is_on=is_on, level=level, group=group, mode=mode,
                            transition=transition, reason=reason)
        except:
            LOG.exception("Invalid SetTopic command: %s", data)

    #-----------------------------------------------------------------------
