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
    """

    def __init__(self, mqtt, device):
        """Constructor

        Args:
          mqtt (mqtt.Mqtt):  The MQTT main interface.
          device (device.Switch):  The Insteon object to link to.
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
        self.msg_scene = MsgTemplate(
            topic='insteon/{{address}}/scene',
            payload='{ "cmd" : "{{value.lower()}}" }')

        # Receive notifications from the Insteon device when it changes.
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
        data = config.get("switch", None)
        if not data:
            return

        # Update the MQTT topics and payloads from the config file.
        self.msg_state.load_config(data, 'state_topic', 'state_payload', qos)
        self.msg_manual_state.load_config(data, 'manual_state_topic',
                                          'manual_state_payload', qos)
        self.msg_on_off.load_config(data, 'on_off_topic', 'on_off_payload',
                                    qos)
        self.msg_scene.load_config(data, 'scene_topic', 'scene_payload', qos)

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
        topic = self.msg_scene.render_topic(self.template_data())
        link.subscribe(topic, qos, self._input_scene)

    #-----------------------------------------------------------------------
    def unsubscribe(self, link):
        """Unsubscribe to any MQTT topics the object was subscribed to.

        Args:
          link (network.Mqtt):  The MQTT network client to use.
        """
        topic = self.msg_on_off.render_topic(self.template_data())
        link.unsubscribe(topic)

        topic = self.msg_scene.render_topic(self.template_data())
        link.unsubscribe(topic)

    #-----------------------------------------------------------------------
    def template_data(self, is_on=None, mode=on_off.Mode.NORMAL,
                      manual=None, reason=None):
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
            data["reason"] = reason if reason is not None else ""

        if manual is not None:
            data["manual_str"] = str(manual)
            data["manual"] = manual.int_value()
            data["manual_openhab"] = manual.openhab_value()
            data["reason"] = reason if reason is not None else ""

        return data

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
    def _insteon_manual(self, device, manual, reason=""):
        """Device manual mode callback.

        This is triggered via signal when the Insteon device starts or stops
        manual mode (holding a button down).  It will publish an MQTT message
        with the new state.

        Args:
          device (device.Base): The Insteon device that changed.
          manual (on_off.Manual):  The manual mode.
          reason (str):  The reason the device was triggered.  This is an
                 arbitrary string set into the template variables.
        """
        LOG.info("MQTT received manual change %s %s '%s'", device.label,
                 manual, reason)

        # For manual mode messages, don't retain them because they don't
        # represent persistent state - they're momentary events.
        data = self.template_data(manual=manual, reason=reason)
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
            reason = data.get("reason", "")
            self.device.set(level=is_on, mode=mode, reason=reason)
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
        data = self.msg_scene.to_json(message.payload)
        LOG.info("Switch input command: %s", data)

        try:
            # Scenes don't support modes so don't parse that element.
            is_on = util.parse_on_off(data, have_mode=False)
            group = int(data.get('group', 0x01))
            reason = data.get("reason", "")

            # Tell the device to trigger the scene command.
            self.device.scene(is_on, group, reason)
        except:
            LOG.exception("Invalid switch scene command: %s", data)

    #-----------------------------------------------------------------------
