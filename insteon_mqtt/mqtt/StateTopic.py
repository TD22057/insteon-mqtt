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
from .ManualTopic import ManualTopic

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

        # Set to false if you do not want messages from this device retained.
        # Currently only used by the battery operated remote
        self.state_retain = True

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
    def state_template_data(self, **kwargs):
        """Create the Jinja templating data variables for on/off messages.

        Args:
          is_on (bool):  The on/off state of the switch.  If None, on/off and
                mode attributes are not added to the data.
          mode (on_off.Mode):  The on/off mode state.
          manual (on_off.Manual):  The manual mode state.  If None, manual
                 attributes are not added to the data.
          reason (str):  The reason the device was triggered.  This is an
                 arbitrary string set into the template variables.

        Returns:
          dict:  Returns a dict with the variables available for templating.
        """
        # Set up the variables that can be used in the templates.
        data = self.base_template_data(**kwargs)

        # Dimmers
        if 'level' in kwargs and kwargs['level'] is not None:
            data["on"] = 1 if kwargs['level'] else 0
            data["on_str"] = "on" if kwargs['level'] else "off"
            data["level_255"] = kwargs['level']
            data["level_100"] = int(100.0 * kwargs['level'] / 255.0)

        # Non-dimmers
        elif 'is_on' in kwargs and kwargs['is_on'] is not None:
            data["on"] = 1 if kwargs['is_on'] else 0
            data["on_str"] = "on" if kwargs['is_on'] else "off"

        # If we have an on value
        if 'on' in data:
            data["mode"] = str(on_off.Mode.NORMAL)
            data["fast"] = 0
            data["instant"] = 0
            if 'mode' in kwargs:
                data["mode"] = str(kwargs['mode'])
                data["fast"] = 1 if kwargs['mode'] == on_off.Mode.FAST else 0
                data["instant"] = 0
                if kwargs['mode'] == on_off.Mode.INSTANT:
                    data["instant"] = 1
            data["reason"] = ""
            if 'reason' in kwargs and kwargs['reason'] is not None:
                data["reason"] = kwargs['reason']

        # Update with manual data
        manual_data = ManualTopic.manual_template_data(**kwargs)
        data.update(manual_data)

        return data
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

        if not self.state_retain:
            retain = False
        else:
            # For manual mode messages, don't retain them because they don't
            # represent persistent state - they're momentary events.
            retain = None
            if 'mode' in kwargs and kwargs['mode'] == on_off.Mode.MANUAL:
                retain = False

        data = self.state_template_data(**kwargs)
        self.msg_state.publish(self.mqtt, data, retain=retain)

    #-----------------------------------------------------------------------
