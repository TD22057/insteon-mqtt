#===========================================================================
#
# MQTT keypad linc which is a dimmer plus 4 or 8 button remote.
#
#===========================================================================
import functools
from .. import log
from .. import on_off
from .MsgTemplate import MsgTemplate
from . import util

LOG = log.get_logger()


class KeypadLinc:
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
        self.mqtt = mqtt
        self.device = device

        # Output on/off state change reporting template.
        self.msg_btn_state = MsgTemplate(
            topic='insteon/{{address}}/state/{{button}}',
            payload='{{on_str.lower()}}')

        # Output manual state change is off by default.
        self.msg_manual_state = MsgTemplate(None, None)

        # Input on/off command template.
        self.msg_btn_on_off = MsgTemplate(
            topic='insteon/{{address}}/set/{{button}}',
            payload='{ "cmd" : "{{value.lower()}}" }')

        # Input scene on/off command template.
        self.msg_btn_scene = MsgTemplate(
            topic='insteon/{{address}}/scene/{{button}}',
            payload='{ "cmd" : "{{value.lower()}}" }')

        self.msg_dimmer_state = None
        self.msg_dimmer_level = None
        if self.device.is_dimmer:
            # Output dimmer state change reporting template.
            self.msg_dimmer_state = MsgTemplate(
                topic='insteon/{{address}}/state/1',
                payload='{ "state" : "{{on_str.lower()}}", '
                        '"brightness" : {{level_255}} }')

            # Input dimmer level command template.
            self.msg_dimmer_level = MsgTemplate(
                topic='insteon/{{address}}/level',
                payload='{ "cmd" : "{{json.state.lower()}}", '
                        '"level" : {{json.brightness}} }')

        # Connect the signals from the insteon device so we get notified of
        # changes.
        device.signal_level_changed.connect(self._insteon_level_changed)
        device.signal_manual.connect(self._insteon_manual)

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

        self.msg_btn_state.load_config(data, 'btn_state_topic',
                                       'btn_state_payload', qos)
        self.msg_manual_state.load_config(data, 'manual_state_topic',
                                          'manual_state_payload', qos)
        self.msg_btn_on_off.load_config(data, 'btn_on_off_topic',
                                        'btn_on_off_payload', qos)
        self.msg_btn_scene.load_config(data, 'btn_scene_topic',
                                       'btn_scene_payload', qos)

        if self.device.is_dimmer:
            self.msg_dimmer_state.load_config(data, 'dimmer_state_topic',
                                              'dimmer_state_payload', qos)
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
            data = self.template_data(button=1)
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

            handler = functools.partial(self._input_scene, group=1)
            topic = self.msg_btn_scene.render_topic(data)
            link.subscribe(topic, qos, handler)

        # We need to subscribe to each button topic so we know which one is
        # which.
        for group in range(start_group, 9):
            handler = functools.partial(self._input_on_off, group=group)
            data = self.template_data(button=group)

            topic = self.msg_btn_on_off.render_topic(data)
            link.subscribe(topic, qos, handler)

            handler = functools.partial(self._input_scene, group=group)
            topic = self.msg_btn_scene.render_topic(data)
            link.subscribe(topic, qos, handler)

    #-----------------------------------------------------------------------
    def unsubscribe(self, link):
        """Unsubscribe to any MQTT topics the object was subscribed to.

        Args:
          link (network.Mqtt):  The MQTT network client to use.
        """
        for group in range(1, 9):
            data = self.template_data(button=group)

            topic = self.msg_btn_on_off.render_topic(data)
            link.unsubscribe(topic)

            topic = self.msg_btn_scene.render_topic(data)
            link.unsubscribe(topic)

        if self.device.is_dimmer:
            data = self.template_data(button=1)
            topic = self.msg_dimmer_level.render_topic(data)
            link.unsubscribe(topic)

    #-----------------------------------------------------------------------
    # pylint: disable=arguments-differ
    def template_data(self, button=None, level=None, mode=on_off.Mode.NORMAL,
                      manual=None):
        """Create the Jinja templating data variables for on/off messages.

        Args:
          button (int):  The button (group) ID (1-8) of the Insteon button
                 that was triggered.
          level (int):  The dimmer level.  If None, on/off, levels, and mode
                attributes are not added to the data.
          mode (on_off.Mode):  The on/off mode state.
          manual (on_off.Manual):  The manual mode state.  If None, manual
                 attributes are not added to the data.

        Returns:
          dict:  Returns a dict with the variables available for templating.
        """
        data = {
            "address" : self.device.addr.hex,
            "name" : self.device.name if self.device.name
                     else self.device.addr.hex,
            "button" : button,
            }

        if level is not None:
            level = int(level)
            data["on"] = 1 if level else 0
            data["on_str"] = "on" if level else "off"
            data["level_255"] = level
            data["level_100"] = int(100.0 * level / 255.0)
            data["mode"] = str(mode)
            data["fast"] = 1 if mode == on_off.Mode.FAST else 0
            data["instant"] = 1 if mode == on_off.Mode.INSTANT else 0

        if manual is not None:
            data["manual_str"] = str(manual)
            data["manual"] = manual.int_value()
            data["manual_openhab"] = manual.openhab_value()

        return data

    #-----------------------------------------------------------------------
    def _insteon_level_changed(self, device, group, level,
                               mode=on_off.Mode.NORMAL):
        """Device on/off and dimmer level changed callback.

        This is triggered via signal when the Insteon device goes active or
        inactive.  It will publish an MQTT message with the new state.

        Args:
          device (device.KeypadLinc):  The Insteon device that changed.
          group (int):  The button (1-8) that was pressed.
          level (int):  The dimmer level (0->255)
          mode (on_off.Mode):  The on/off mode state.
        """
        LOG.info("MQTT received button press %s = btn %s at %s %s",
                 device.label, group, level, mode)

        data = self.template_data(group, level, mode)

        # For manual mode messages, don't retain them because they don't
        # represent persistent state - they're momentary events.
        retain = False if mode == on_off.Mode.MANUAL else None

        if group == 1 and self.device.is_dimmer:
            self.msg_dimmer_state.publish(self.mqtt, data, retain=retain)
        else:
            self.msg_btn_state.publish(self.mqtt, data, retain=retain)

    #-----------------------------------------------------------------------
    def _insteon_manual(self, device, group, manual):
        """Device manual mode changed callback.

        This is triggered via signal when the Insteon device starts or stops
        manual mode (holding a button down).  It will publish an MQTT message
        with the new state.

        Args:
          device (device.Dimmer):  The Insteon device that changed.
          group (int):  The button (1-8) that was pressed.
          manual (on_off.Manual):  The manual mode.
        """
        LOG.info("MQTT received manual button press %s = btn %s %s",
                 device.label, group, manual)

        # For manual mode messages, don't retain them because they don't
        # represent persistent state - they're momentary events.
        data = self.template_data(group, manual=manual)
        self.msg_manual_state.publish(self.mqtt, data, retain=False)

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
            is_on, mode = util.parse_on_off(data)
            level = 0xff if is_on else 0x00
            self.device.set(level, group, mode)
        except:
            LOG.exception("Invalid KeypadLinc on/off command: %s", data)
            if raise_errors:
                raise

    #-----------------------------------------------------------------------
    def _input_set_level(self, client, data, message, raise_errors=False):
        """Handle an input level changechange MQTT message.

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
            is_on, mode = util.parse_on_off(data)
            level = 0 if not is_on else int(data.get('level'))
            self.device.set(level, mode=mode)
        except:
            LOG.exception("Invalid KeypadLinc level command: %s", data)
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

    #-----------------------------------------------------------------------
    def _input_scene(self, client, data, message, group):
        """Handle an input scene MQTT message.

        This is called when we receive a message on the scene trigger MQTT
        topic subscription.  Parse the message and pass the command to the
        Insteon device.

        Args:
          client (paho.Client):  The paho mqtt client (self.link).
          data:  Optional user data (unused).
          message:  MQTT message - has attrs: topic, payload, qos, retain.
        """
        LOG.debug("KeypadLinc scene %s message %s %s", group, message.topic,
                  message.payload)

        # Parse the input MQTT message.
        data = self.msg_btn_scene.to_json(message.payload)
        if not data:
            return

        LOG.info("KeypadLinc input command: %s", data)
        try:
            # Scenes don't support modes so don't parse that element.
            is_on = util.parse_on_off(data, have_mode=False)
            self.device.scene(is_on, group)
        except:
            LOG.exception("Invalid KeypadLinc command: %s", data)

    #-----------------------------------------------------------------------
