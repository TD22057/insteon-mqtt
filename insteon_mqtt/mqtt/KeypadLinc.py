#===========================================================================
#
# MQTT keypad linc which is a dimmer plus 4 or 8 button remote.
#
#===========================================================================
import functools
from .. import log
from .MsgTemplate import MsgTemplate
from . import util
from .SceneTopic import SceneTopic
from .StateTopic import StateTopic
from .ManualTopic import ManualTopic

LOG = log.get_logger()


class KeypadLinc(SceneTopic, StateTopic, ManualTopic):
    """MQTT interface to an Insteon KeypadLinc dimmer or switch.

    This class connects to a device.KeypadLinc object and converts it's output
    state changes to MQTT messages.  It also subscribes to topics to allow
    input MQTT messages to change the state of the Insteon device.

    KeypadLinc are either dimmers or switches for the main load and switches
    for the other buttons on the device.
    """
    def __init__(self, mqtt, device):
        """Constructor

        Args:
          mqtt (mqtt.Mqtt):  The MQTT main interface.
          device (device.KeypadLinc):  The Insteon object to link to.
        """
        # Setup a special template for button one if this is a dimmer
        state_payload_1 = None
        if device.is_dimmer:
            state_payload_1 = '{ "state" : "{{on_str.lower()}}", ' \
                              '"brightness" : {{level_255}} }'
        super().__init__(mqtt, device,
                         scene_topic='insteon/{{address}}/scene/{{button}}',
                         state_topic='insteon/{{address}}/state/{{button}}',
                         state_payload_1=state_payload_1,)

        # Input on/off command template.
        self.msg_btn_on_off = MsgTemplate(
            topic='insteon/{{address}}/set/{{button}}',
            payload='{ "cmd" : "{{value.lower()}}" }')

        self.msg_dimmer_level = None
        if self.device.is_dimmer:
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

        # Load the various topics
        self.load_state_data(data, qos,
                             topic='btn_state_topic',
                             payload='btn_state_payload')
        self.load_manual_data(data, qos)
        self.load_scene_data(data, qos,
                             topic='btn_scene_topic',
                             payload='btn_scene_payload')

        self.msg_btn_on_off.load_config(data, 'btn_on_off_topic',
                                        'btn_on_off_payload', qos)

        if self.device.is_dimmer:
            self.msg_dimmer_level.load_config(data, 'dimmer_level_topic',
                                              'dimmer_level_payload', qos)

    #-----------------------------------------------------------------------
    def subscribe(self, link, qos):
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
        start_group = 1
        if self.device.is_dimmer:
            start_group = 2

            # Create the topic names for button 1.
            data = self.base_template_data(button=1)
            topic_switch = self.msg_btn_on_off.render_topic(data)
            topic_dimmer = self.msg_dimmer_level.render_topic(data)

            # It's possible for these to be the same.  The btn1 handler will
            # try both payloads to accept either on/off or dimmer commands.
            if topic_switch == topic_dimmer:
                link.subscribe(topic_switch, qos, self._input_btn1)

            # If they are different, we can pass directly to the right
            # handler for switch commands and dimmer commands.
            else:
                handler = functools.partial(self._input_on_off, group=1)
                link.subscribe(topic_switch, qos, handler)

                link.subscribe(topic_dimmer, qos, self._input_set_level)

            # Add the Scene Topic
            self.scene_subscribe(link, qos, group=1)

        # We need to subscribe to each button topic so we know which one is
        # which.
        for group in range(start_group, 9):
            handler = functools.partial(self._input_on_off, group=group)
            data = self.base_template_data(button=group)

            topic = self.msg_btn_on_off.render_topic(data)
            link.subscribe(topic, qos, handler)

            # Add the Scene Topic
            self.scene_subscribe(link, qos, group=group)

    #-----------------------------------------------------------------------
    def unsubscribe(self, link):
        """Unsubscribe to any MQTT topics the object was subscribed to.

        Args:
          link (network.Mqtt):  The MQTT network client to use.
        """
        for group in range(1, 9):
            data = self.base_template_data(button=group)

            topic = self.msg_btn_on_off.render_topic(data)
            link.unsubscribe(topic)

            # Remove the Scene Topic
            self.scene_unsubscribe(link, group=group)

        if self.device.is_dimmer:
            data = self.base_template_data(button=1)
            topic = self.msg_dimmer_level.render_topic(data)
            link.unsubscribe(topic)

    #-----------------------------------------------------------------------
    def _input_on_off(self, client, data, message, group, raise_errors=False):
        """Handle an input on/off change MQTT message.

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
        LOG.info("KeypadLinc btn %s message %s %s", group, message.topic,
                 message.payload)

        data = self.msg_btn_on_off.to_json(message.payload)
        if not data:
            return

        LOG.info("KeypadLinc btn %s input command: %s", group, data)
        try:
            is_on, mode, transition = util.parse_on_off(data)
            level = None if is_on else 0x00
            reason = data.get("reason", "")
            self.device.set(is_on=is_on, level=level, group=group, mode=mode,
                            reason=reason, transition=transition)
        except:
            LOG.error("Invalid KeypadLinc on/off command: %s", data)
            if raise_errors:
                raise

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
        try:
            is_on, mode, transition = util.parse_on_off(data)
            level = '0' if not is_on else data.get('level')
            if level is not None:
                level = int(level)
            reason = data.get("reason", "")
            self.device.set(is_on=is_on, level=level, mode=mode, reason=reason,
                            transition=transition)
        except:
            LOG.error("Invalid KeypadLinc level command: %s", data)
            if raise_errors:
                raise

    #-----------------------------------------------------------------------
    def _input_btn1(self, client, data, message):
        """Handle button 1 when the on/off topic == dimmer topic

        This is called when we receive a message on the level change MQTT
        topic subscription.  Parse the message and pass the command to the
        Insteon device.

        Args:
          client (paho.Client):  The paho mqtt client (self.link).
          data:  Optional user data (unused).
          message:  MQTT message - has attrs: topic, payload, qos, retain.
        """
        LOG.info("KeypadLinc message %s %s", message.topic, message.payload)

        # Try the input as a dimmer command first.
        try:
            if self.msg_dimmer_level.to_json(message.payload, silent=True):
                self._input_set_level(client, data, message, raise_errors=True)
                return
        except:
            pass

        # Try the input as an on/off command.
        try:
            if self.msg_btn_on_off.to_json(message.payload, silent=True):
                self._input_on_off(client, data, message, group=1,
                                   raise_errors=True)
                return
        except:
            pass

        # If we make it here, it's an error.
        LOG.error("Invalid input command did match a dimmer or on/off "
                  "message: %s", message.payload)
