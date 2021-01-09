#===========================================================================
#
# MQTT State Topic
#
#===========================================================================
import functools
from .. import log
from .. import on_off
from .MsgTemplate import MsgTemplate
from . import util

LOG = log.get_logger()


class StateTopic:
    """MQTT interface to the State Topic

    This is an abstract class that provides support for the State topic.
    """
    def __init__(self, state_topic=None, state_payload=None, **kwargs):
        """Constructor

        """
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
        self.device.signal_on_off.connect(self._insteon_on_off)

        super().__init__(**kwargs)

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
    def template_data(self, *args, **kwargs):
        raise NotImplementedError  # pragma: no cover

    #-----------------------------------------------------------------------
    def _insteon_on_off(self, device, is_on, mode=on_off.Mode.NORMAL,
                        reason=""):
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
        LOG.info("MQTT received on/off %s on: %s %s '%s'", device.label, is_on,
                 mode, reason)

        # For manual mode messages, don't retain them because they don't
        # represent persistent state - they're momentary events.
        retain = False if mode == on_off.Mode.MANUAL else None

        data = self.template_data(is_on, mode, reason=reason)
        self.msg_state.publish(self.mqtt, data, retain=retain)

    #-----------------------------------------------------------------------
