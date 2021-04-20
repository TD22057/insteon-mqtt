#===========================================================================
#
# MQTT State Topic
#
#===========================================================================
from ... import log
from ... import on_off
from ..MsgTemplate import MsgTemplate
from .BaseTopic import BaseTopic
from .ManualTopic import ManualTopic

LOG = log.get_logger()


class StateTopic(BaseTopic):
    """MQTT interface to the State Topic

    This is an abstract class that provides support for the State topic.
    """
    def __init__(self, mqtt, device, state_topic=None, state_payload=None,
                 state_topic_1=None, state_payload_1=None, **kwargs):
        """State Topic Constructor

        Args:
          device (device):  The Insteon object to link to.
          mqtt (mqtt.Mqtt):  The MQTT main interface.
          state_topic (str): A string of the jinja template for the topic
          state_payload (str): A string of the jinja template for the payload
          state_topic_1 (str): A string of the jinja template for the topic of
                               group 1 if it is distinct from other groups.
                               Only the KPL Dimmer uses this.
          state_payload_1 (str): A string of the jinja template for the payload
                                 of group 1 if it is distinct from other
                                 groups. Only the KPL Dimmer uses this.
          mqtt (mqtt.Mqtt):  The MQTT main interface.
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

        # Set a disctinct template for button 1 if asked.  Only used for KPL
        # Dimmer
        self.msg_state_1 = None
        if state_topic_1 is not None or state_payload_1 is not None:
            if state_topic_1 is None:
                state_topic_1 = state_topic
            if state_payload_1 is None:
                state_payload_1 = state_payload
            self.msg_state_1 = MsgTemplate(
                topic=state_topic_1,
                payload=state_payload_1)

        # Receive notifications from the Insteon device when it changes.
        self.device.signal_state.connect(self.publish_state)

        # Set to false if you do not want messages from this device retained.
        # Currently only used by the battery operated remote
        self.state_retain = True

    #-----------------------------------------------------------------------
    def load_state_data(self, data, qos=None, topic=None, payload=None,
                        topic_1=None, payload_1=None):
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

        if self.msg_state_1 is not None:
            if topic_1 is None:
                topic_1 = 'dimmer_state_topic'
            if payload_1 is None:
                payload_1 = 'dimmer_state_payload'
            self.msg_state_1.load_config(data, topic_1, payload_1, qos)
            # Add ourselves to the list of topics
            self.rendered_topic_map['dimmer_state_topic'] = self.msg_state_1.render_topic(
                self.base_template_data()
            )

        if len(self.group_state_list) > 0:
            # This device has multiple state topics for multiple buttons
            data = self.base_template_data()
            for btn in self.group_state_list:
                data['button'] = btn
                self.rendered_topic_map['state_topic_' + str(btn)] = self.msg_state.render_topic(
                    data
                )
        else:
            # Add ourselves to the list of topics
            self.rendered_topic_map['state_topic'] = self.msg_state.render_topic(
                self.base_template_data()
            )

    #-----------------------------------------------------------------------
    def state_template_data(self, **kwargs):
        """Create the Jinja templating data variables for on/off messages.

        kwargs includes:
          is_on (bool):  The on/off state of the switch.  If None, on/off and
                mode attributes are not added to the data.
          mode (on_off.Mode):  The on/off mode state.
          manual (on_off.Manual):  The manual mode state.  If None, manual
                 attributes are not added to the data.
          reason (str):  The reason the device was triggered.  This is an
                 arbitrary string set into the template variables.
          level (int):  A brightness level between 0-255
          button (int): Passed to base_template_data, the group numer to use

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
          device (device):   The Insteon device that changed.
          kwargs (dict): The arguments to pass to state_template_data
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

        # If this has a distinct template for group 1 use it.
        button = kwargs.get('button', None)
        if (button == 1 or button is None) and self.msg_state_1 is not None:
            self.msg_state_1.publish(self.mqtt, data, retain=retain)
        else:
            self.msg_state.publish(self.mqtt, data, retain=retain)

    #-----------------------------------------------------------------------
