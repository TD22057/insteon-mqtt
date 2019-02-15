#===========================================================================
#
# MQTT On/Off switch device
#
#===========================================================================
from .. import log
from .. import on_off
from .MsgTemplate import MsgTemplate
from . import util

LOG = log.get_logger()


class Switch:
    """MQTT interface to an Insteon on/off switch.

    This class connects to a device.Switch object and converts it's
    output state changes to MQTT messages.  It also subscribes to topics to
    allow input MQTT messages to change the state of the Insteon device.

    Switches will report their state and can be commanded to turn on and off.

    Some classes that can act like a switch can inherit from this class to
    use the same MQTT templates (see Dimmer).
    """

    def __init__(self, mqtt, device, connect_signals=True):
        """Constructor

        Args:
          mqtt (mqtt.Mqtt):  The MQTT main interface.
          device (device.Switch):  The Insteon object to link to.
          connect_signals (bool):  If True, connect the signal_active signal
                          from the device to this class.  If False, the
                          connection is handled elsewhere.  This is commonly
                          used by derived classes to stop the switch from
                          connecting signals.
        """
        self.mqtt = mqtt
        self.device = device

        # Output state change reporting template.
        self.msg_state = MsgTemplate(
            topic='insteon/{{address}}/state',
            payload='{{on_str.lower()}}')

        # Output manual state change is off by default.
        self.msg_manual_state = MsgTemplate(None, None)

        # Input on/off command template.
        self.msg_on_off = MsgTemplate(
            topic='insteon/{{address}}/set',
            payload='{ "cmd" : "{{value.lower()}}" }')

        # Input scene on/off command template.
        self.msg_scene_on_off = MsgTemplate(
            topic='insteon/{{address}}/scene',
            payload='{ "cmd" : "{{value.lower()}}" }')

        # Receive notifications from the Insteon device when it changes.
        if connect_signals:
            device.signal_on_off.connect(self._insteon_on_off)
            device.signal_manual.connect(self._insteon_manual)

    #-----------------------------------------------------------------------
    def load_config(self, config, qos=None):
        """Load values from a configuration data object.

        Args:
          config (dict:  The configuration dictionary to load from.  The object
                 config is stored in config['switch'].
          qos (int):  The default quality of service level to use.
        """
        self.load_switch_config(config.get("switch", None), qos)

    #-----------------------------------------------------------------------
    def load_switch_config(self, config, qos):
        """Load the switch portion of the configuration.

        This is factored out of load_config() so derived classes can call it
        directly if needed.

        Args:
          config (dict:  The configuration dictionary to load from.  The object
                 config is stored in config['switch'].
          qos (int):  The default quality of service level to use.
        """
        if not config:
            return

        # Update the MQTT topics and payloads from the config file.
        self.msg_state.load_config(config, 'state_topic', 'state_payload', qos)
        self.msg_manual_state.load_config(config, 'manual_state_topic',
                                          'manual_state_payload', qos)
        self.msg_on_off.load_config(config, 'on_off_topic', 'on_off_payload',
                                    qos)
        self.msg_scene_on_off.load_config(config, 'scene_on_off_topic',
                                          'scene_on_off_payload', qos)

    #-----------------------------------------------------------------------
    def subscribe(self, link, qos):
        """Subscribe to any MQTT topics the object needs.

        Subscriptions are used when the object has things that can be
        commanded to change.

        Args:
          link (network.Mqtt):  The MQTT network client to use.
          qos (int):  The quality of service to use.
        """
        # On/off command messages.
        topic = self.msg_on_off.render_topic(self.template_data())
        link.subscribe(topic, qos, self._input_on_off)

        # Scene triggering messages.
        topic = self.msg_scene_on_off.render_topic(self.template_data())
        link.subscribe(topic, qos, self._input_scene)

    #-----------------------------------------------------------------------
    def unsubscribe(self, link):
        """Unsubscribe to any MQTT topics the object was subscribed to.

        Args:
          link (network.Mqtt):  The MQTT network client to use.
        """
        topic = self.msg_on_off.render_topic(self.template_data())
        link.unsubscribe(topic)

        topic = self.msg_scene_on_off.render_topic(self.template_data())
        link.unsubscribe(topic)

    #-----------------------------------------------------------------------
    def template_data(self, is_on=None, mode=on_off.Mode.NORMAL,
                      manual=None):
        """Create the Jinja templating data variables for on/off messages.

        Args:
          is_on (bool):  The on/off state of the switch.  If None, on/off and
                mode attributes are not added to the data.
          mode (on_off.Mode):  The on/off mode state.
          manual (on_off.Manual):  The manual mode state.  If None, manual
                attributes are not added to the data.

        Returns:
          dict:  Returns a dict with the variables available for templating.
        """
        # Set up the variables that can be used in the templates.
        data = {
            "address" : self.device.addr.hex,
            "name" : self.device.name if self.device.name
                     else self.device.addr.hex,
            }

        if is_on is not None:
            data["on"] = 1 if is_on else 0
            data["on_str"] = "on" if is_on else "off"
            data["mode"] = str(mode)
            data["fast"] = 1 if mode == on_off.Mode.FAST else 0
            data["instant"] = 1 if mode == on_off.Mode.INSTANT else 0

        if manual is not None:
            data["manual_str"] = str(manual)
            data["manual"] = manual.int_value()
            data["manual_openhab"] = manual.openhab_value()

        return data

    #-----------------------------------------------------------------------
    def _insteon_on_off(self, device, is_on, mode=on_off.Mode.NORMAL):
        """Device on/off callback.

        This is triggered via signal when the Insteon device is turned on or
        off.  It will publish an MQTT message with the new state.

        Args:
          device (device.Switch):   The Insteon device that changed.
          is_on (bool):   True for on, False for off.
          mode (on_off.Mode):  The on/off mode state.
        """
        LOG.info("MQTT received on/off %s on: %s %s", device.label, is_on,
                 mode)

        # For manual mode messages, don't retain them because they don't
        # represent persistent state - they're momentary events.
        retain = False if mode == on_off.Mode.MANUAL else None

        data = self.template_data(is_on, mode)
        self.msg_state.publish(self.mqtt, data, retain=retain)

    #-----------------------------------------------------------------------
    def _insteon_manual(self, device, manual):
        """Device manual mode callback.

        This is triggered via signal when the Insteon device starts or stops
        manual mode (holding a button down).  It will publish an MQTT message
        with the new state.

        Args:
          device:   (device.Base) The Insteon device that changed.
          manual:   (on_off.Manual) The manual mode.
        """
        LOG.info("MQTT received manual change %s %s", device.label, manual)

        # For manual mode messages, don't retain them because they don't
        # represent persistent state - they're momentary events.
        data = self.template_data(manual=manual)
        self.msg_manual_state.publish(self.mqtt, data, retain=False)

    #-----------------------------------------------------------------------
    def _input_on_off(self, client, data, message):
        """Handle an input on/off change MQTT message.

        This is called when we receive a message on the on/off MQTT topic
        subscription.  Parse the message and pass the command to the Insteon
        device.

        Args:
          client (paho.Client):  The paho mqtt client (self.link).
          data:  Optional user data (unused).
          message:  MQTT message - has attrs: topic, payload, qos, retain.
        """
        LOG.debug("Switch message %s %s", message.topic, message.payload)

        # Parse the input MQTT message.
        data = self.msg_on_off.to_json(message.payload)
        LOG.info("Switch input command: %s", data)

        try:
            # Tell the device to update it's state.
            is_on, mode = util.parse_on_off(data)
            self.device.set(level=is_on, mode=mode)
        except:
            LOG.exception("Invalid switch on/off command: %s", data)

    #-----------------------------------------------------------------------
    def _input_scene(self, client, data, message):
        """Handle an input scene MQTT message.

        This is called when we receive a message on the scene trigger MQTT
        topic subscription.  Parse the message and pass the command to the
        Insteon device.

        Args:
          client (paho.Client):  The paho mqtt client (self.link).
          data:  Optional user data (unused).
          message:  MQTT message - has attrs: topic, payload, qos, retain.
        """
        LOG.debug("Switch message %s %s", message.topic, message.payload)

        # Parse the input MQTT message.
        data = self.msg_scene_on_off.to_json(message.payload)
        LOG.info("Switch input command: %s", data)

        try:
            is_on, _mode = util.parse_on_off(data)
            group = int(data.get('group', 0x01))

            # Tell the device to trigger the scene command.
            self.device.scene(is_on, group)
        except:
            LOG.exception("Invalid switch scene command: %s", data)

    #-----------------------------------------------------------------------
