#===========================================================================
#
# MQTT keypad linc which is a dimmer with 4 or 8 button
#
#===========================================================================
from .. import log
from .MsgTemplate import MsgTemplate
from . import util
from .KeypadLinc import KeypadLinc

LOG = log.get_logger()


class KeypadLincDimmer(KeypadLinc):
    """MQTT interface to an Insteon KeypadLinc dimmer.

    This class connects to a device.KeypadLinc object and converts it's output
    state changes to MQTT messages.  It also subscribes to topics to allow
    input MQTT messages to change the state of the Insteon device.

    This class is an extension of the KeypadLinc switch class
    """
    def __init__(self, mqtt, device):
        """Constructor

        Args:
          mqtt (mqtt.Mqtt):  The MQTT main interface.
          device (device.KeypadLinc):  The Insteon object to link to.
        """
        # Setup a special template for button one if this is a dimmer
        state_payload_1 = '{ "state" : "{{on_str.lower()}}", ' \
                          '"brightness" : {{level_255}} }'
        super().__init__(mqtt, device, state_payload_1=state_payload_1)

        # Input dimmer level command template.
        self.msg_dimmer_level = MsgTemplate(
            topic='insteon/{{address}}/level',
            payload='{ "cmd" : "{{json.state.lower()}}", '
                    '"level" : {{json.brightness}} }')

    #-----------------------------------------------------------------------
    def load_config(self, config, qos=None):
        """Load values from a configuration data object.

        Args:
          config (dict:  The configuration dictionary to load from.  The object
                 config is stored in config['keypad_linc'].
          qos (int):  The default quality of service level to use.
        """
        data = config.get("keypad_linc", None)
        if not data:
            return
        super().load_config(config, qos=qos)
        self.msg_dimmer_level.load_config(data, 'dimmer_level_topic',
                                          'dimmer_level_payload', qos)

        # Add our unique topics to the discovery topic map
        topics = {}
        topics['dimmer_level_topic'] = self.msg_dimmer_level.render_topic(
            self.base_template_data()
        )
        self.rendered_topic_map.update(topics)

    #-----------------------------------------------------------------------
    def subscribe(self, link, qos, start_group=1):
        """Subscribe to any MQTT topics the object needs.

        Subscriptions are used when the object has things that can be
        commanded to change.

        Args:
          link (network.Mqtt):  The MQTT network client to use.
          qos (int):  The quality of service to use.
        """
        # For dimmers, the button 1 set can be either an on/off or a dimming
        # command.  And the dimmer topic might have the same topic as the
        # on/off command.
        start_group = 2

        # If the on/off and level topics are the same, send to level
        # otherwise instantiate both.
        data = self.base_template_data(button=1)
        topic_switch = self.msg_set.render_topic(data)
        topic_dimmer = self.msg_dimmer_level.render_topic(data)
        if topic_switch == topic_dimmer:
            data = self.base_template_data(button=1)
            topic_dimmer = self.msg_dimmer_level.render_topic(data)
            link.subscribe(topic_dimmer, qos, self._input_set_level)
        else:
            self.set_subscribe(link, qos, group=1)
            # Create the topic names for button 1.
            data = self.base_template_data(button=1)
            topic_dimmer = self.msg_dimmer_level.render_topic(data)
            link.subscribe(topic_dimmer, qos, self._input_set_level)

        # Add the Scene Topic
        self.scene_subscribe(link, qos, group=1)

        # We need to subscribe to each button topic so we know which one is
        # which.
        super().subscribe(link, qos, start_group=start_group)

    #-----------------------------------------------------------------------
    def unsubscribe(self, link):
        """Unsubscribe to any MQTT topics the object was subscribed to.

        Args:
          link (network.Mqtt):  The MQTT network client to use.
        """
        super().unsubscribe(link)

        data = self.base_template_data(button=1)
        topic_str = self.msg_dimmer_level.render_topic(data)
        link.unsubscribe(topic_str)

    #-----------------------------------------------------------------------
    def _input_set_level(self, client, data, message, raise_errors=False):
        """Handle an input level change MQTT message.

        This is called when we receive a message on the level change MQTT
        topic subscription.  Parse the message and pass the command to the
        Insteon device.

        Args:
          client (paho.Client):  The paho mqtt client (self.link).
          data:  Optional user data (unused).
          message:  MQTT message - has attrs: topic, payload, qos, retain.
          raise_errors (bool):  True to raise any errors - otherwise they
                       are logged and ignored.
        """
        LOG.info("KeypadLinc message %s %s", message.topic, message.payload)
        assert self.msg_dimmer_level is not None

        data = self.msg_dimmer_level.to_json(message.payload)
        if not data:
            return

        LOG.info("KeypadLinc input command: %s", data)
        level_str = data.get('level', None)
        if level_str is None or level_str == "":
            # Dimmer and command topic can be the same
            # If this lacks a level command it is meant for on/off
            self._input_set(client, data, message)
        else:
            try:
                is_on, mode, transition = util.parse_on_off(data)
                level = '0' if not is_on else data.get('level', None)
                if level is not None:
                    level = int(level)
                reason = data.get("reason", "")
                self.device.set(is_on=is_on, level=level, mode=mode,
                                reason=reason, transition=transition)
            except:
                LOG.error("Invalid KeypadLinc level command: %s", data)
