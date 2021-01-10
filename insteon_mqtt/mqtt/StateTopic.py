#===========================================================================
#
# MQTT State Topic
#
#===========================================================================
# import functools
from .. import log
from .. import on_off
from .MsgTemplate import MsgTemplate
# from . import util
from .BaseTopic import BaseTopic

LOG = log.get_logger()


class StateTopic(BaseTopic):
    """MQTT interface to the State Topic

    This is an abstract class that provides support for the State topic.
    """
    def __init__(self, mqtt, device, state_topic=None, state_payload=None,
                 **kwargs):
        """Constructor

        """
        super().__init__(mqtt, device, **kwargs)
        # It looks cleaner setting these long strings here rather than in the
        # function declaration
        if state_topic is None:
            state_topic = 'insteon/{{address}}/state'
        if state_payload is None:
            state_payload = '{{on_str.lower()}}'

        LOG.debug("%s, %s", state_topic, state_payload)

        # Output state on/off command template.
        self.msg_state = MsgTemplate(
            topic=state_topic,
            payload=state_payload)

        # Receive notifications from the Insteon device when it changes.
        self.device.signal_state.connect(self.publish_state)

    #-----------------------------------------------------------------------
    def load_state_data(self, data, qos=None, topic=None, payload=None):
        """Load values from a configuration data object.

        Args:
          data (dict):  The section of the config dict that applies to this
                        class.
          qos (int):  The default quality of service level to use.
        """
        if topic is None:
            topic = 'state_topic'
        if payload is None:
            payload = 'state_payload'
        # Update the MQTT topics and payloads from the config file.
        self.msg_state.load_config(data, topic, payload, qos)

    #-----------------------------------------------------------------------
    def template_data(self, **kwargs):
        raise NotImplementedError  # pragma: no cover

    #-----------------------------------------------------------------------
    def publish_state(self, device, **kwargs):
        """Device on/off callback.

        This is triggered via signal when the Insteon device is turned on or
        off.  It will publish an MQTT message with the new state.

        Args:
          device (device.Switch):   The Insteon device that changed.
          is_on (bool):   True for on, False for off.
          mode (on_off.Mode):  The on/off mode state.
          reason (str):  The reason the device was triggered.  This is an
                 arbitrary string set into the template variables.
        """
        LOG.info("MQTT received state %s on: %s", device.label, kwargs)

        # For manual mode messages, don't retain them because they don't
        # represent persistent state - they're momentary events.
        retain = None
        if 'mode' in kwargs:
            retain = False if kwargs['mode'] == on_off.Mode.MANUAL else None

        data = self.template_data(**kwargs)
        self.msg_state.publish(self.mqtt, data, retain=retain)

    #-----------------------------------------------------------------------
