#===========================================================================
#
# MQTT Manual Topic
#
#===========================================================================
from ... import log
from ..MsgTemplate import MsgTemplate
from .BaseTopic import BaseTopic

LOG = log.get_logger()


class ManualTopic(BaseTopic):
    """MQTT interface to the Manual Topic

    This is an abstract class that provides support for the manual topic.

    Output manual state change is off by default.
    """
    @staticmethod
    def manual_template_data(**kwargs):
        """Generate the manual template data

        This is used in StateTopic as well by devices that do not necessarily
        have a ManualTopic.  Not sure if this is necessary, but to enable such
        functionality, this is a static method.
        """
        data = {}
        if 'manual' in kwargs and kwargs['manual'] is not None:
            data["manual_str"] = str(kwargs['manual'])
            data["manual"] = kwargs['manual'].int_value()
            data["manual_openhab"] = kwargs['manual'].openhab_value()
            data["reason"] = ""
            if 'reason' in kwargs and kwargs['reason'] is not None:
                data["reason"] = kwargs['reason']
        return data

    def __init__(self, mqtt, device, manual_topic=None, manual_payload=None,
                 **kwargs):
        """Manual Topic Constructor

        Manual topics are off by default.

        Args:
          mqtt (mqtt.Mqtt):  The MQTT main interface.
          device (device):  The Insteon object to link to.
          manual_topic (str): The template for the topic
          manual_payload (str): The tempalte for the payload
        """
        super().__init__(mqtt, device, **kwargs)

        LOG.debug("%s, %s", manual_topic, manual_payload)

        # Output manual on/off command template.
        self.msg_manual_state = MsgTemplate(topic=manual_topic,
                                            payload=manual_payload)

        # Receive notifications from the Insteon device when it changes.
        self.device.signal_manual.connect(self.publish_manual)

    #-----------------------------------------------------------------------
    def load_manual_data(self, data, qos=None, topic=None, payload=None):
        """Load values from a configuration data object.

        Args:
          data (dict):  The section of the config dict that applies to this
                        class.
          qos (int):  The default quality of service level to use.
        """
        if topic is None:
            topic = 'manual_state_topic'
        if payload is None:
            payload = 'manual_state_payload'

        # Update the MQTT topics and payloads from the config file.
        self.msg_manual_state.load_config(data, topic, payload, qos)

        # Add ourselves to the list of topics
        self.rendered_topic_map[topic] = self.msg_manual_state.render_topic(
            self.base_template_data()
        )

    #-----------------------------------------------------------------------
    def publish_manual(self, device, **kwargs):
        """Device Manual Change Callback.

        This is triggered via signal when the Insteon device is manual change
        is triggered.  It will publish an MQTT message with the new manual.

        Args:
          device (device):   The Insteon device that changed.
          kwargs (dict):  The dictionary of values to pass to template.
        """
        LOG.info("MQTT received manual change %s on: %s", device.label, kwargs)
        data = ManualTopic.manual_template_data(**kwargs)
        # update data with base data
        base_data = self.base_template_data(**kwargs)
        data.update(base_data)
        self.msg_manual_state.publish(self.mqtt, data, retain=False)

    #-----------------------------------------------------------------------
