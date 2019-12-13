#===========================================================================
#
# MQTT dimmer switch device
#
#===========================================================================
from .. import log
from .. import on_off
from .MsgTemplate import MsgTemplate
from . import util

LOG = log.get_logger()


class Dimmer:
    """MQTT interface to an Insteon dimmer switch.

    This class connects to a device.Dimmer object and converts it's output
    state changes to MQTT messages.  It also subscribes to topics to allow
    input MQTT messages to change the state of the Insteon device.

    Dimmers will report their state and brightness (level) and can be
    commanded to turn on and off or on at a specific level (0-255).
    """
    def __init__(self, mqtt, device):
        """Constructor

        Args:
          mqtt (mqtt.Mqtt):  The MQTT main interface.
          device (device.Dimmer):  The Insteon object to link to.
        """
        self.mqtt = mqtt
        self.device = device

        # Output state change reporting template.
        self.msg_state = MsgTemplate(
            topic='insteon/{{address}}/state',
            payload='{ "state" : "{{on_str.lower()}}", '
                    '"brightness" : {{level_255}} }')

        # Output manual state change is off by default.
        self.msg_manual_state = MsgTemplate(None, None)

        # Input on/off command template.
        self.msg_on_off = MsgTemplate(
            topic='insteon/{{address}}/set',
            payload='{ "cmd" : "{{value.lower()}}" }')

        # Input level command template.
        self.msg_level = MsgTemplate(
            topic='insteon/{{address}}/level',
            payload='{ "cmd" : "{{json.state.lower()}}", '
                    '"level" : {{json.brightness}} }')

        # Input scene on/off command template.
        self.msg_scene = MsgTemplate(
            topic='insteon/{{address}}/scene',
            payload='{ "cmd" : "{{value.lower()}}" }')

        # Connect the signals from the insteon device so we get notified of
        # changes.
        device.signal_level_changed.connect(self._insteon_level_changed)
        device.signal_manual.connect(self._insteon_manual)

    #-----------------------------------------------------------------------
    def load_config(self, config, qos=None):
        """Load values from a configuration data object.

        Args:
          config (dict:  The configuration dictionary to load from.  The object
                 config is stored in config['dimmer'].
          qos (int):  The default quality of service level to use.
        """
        data = config.get("dimmer", None)
        if not data:
            return

        # Update the MQTT topics and payloads from the config file.
        self.msg_state.load_config(data, 'state_topic', 'state_payload', qos)
        self.msg_manual_state.load_config(data, 'manual_state_topic',
                                          'manual_state_payload', qos)
        self.msg_on_off.load_config(data, 'on_off_topic', 'on_off_payload',
                                    qos)
        self.msg_level.load_config(data, 'level_topic', 'level_payload', qos)
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

        # Level changing command messages.
        topic = self.msg_level.render_topic(self.template_data())
        link.subscribe(topic, qos, self._input_set_level)

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

        topic = self.msg_level.render_topic(self.template_data())
        link.unsubscribe(topic)

        topic = self.msg_scene.render_topic(self.template_data())
        link.unsubscribe(topic)

    #-----------------------------------------------------------------------
    # pylint: disable=arguments-differ
    def template_data(self, level=None, mode=on_off.Mode.NORMAL, manual=None,
                      reason=None):
        """Create the Jinja templating data variables for on/off messages.

        Args:
          level (int):  The dimmer level.  If None, on/off and levels
                attributes are not added to the data.
          mode (on_off.Mode):  The on/off mode state.
          manual (on_off.Manual):  The manual mode state.  If None, manual
                 attributes are not added to the data.
          reason (str):  The reason the device was triggered.  This is an
                 arbitrary string set into the template variables.

        Returns:
          dict:  Returns a dict with the variables available for templating.
        """
        data = {
            "address" : self.device.addr.hex,
            "name" : self.device.name if self.device.name
                     else self.device.addr.hex,
            }

        if level is not None:
            data["on"] = 1 if level else 0
            data["on_str"] = "on" if level else "off"
            data["level_255"] = level
            data["level_100"] = int(100.0 * level / 255.0)
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
    def _insteon_level_changed(self, device, level, mode=on_off.Mode.NORMAL,
                               reason=""):
        """Device on/off and dimmer level changed callback.

        This is triggered via signal when the Insteon device goes active or
        inactive.  It will publish an MQTT message with the new state.

        Args:
          device (device.Dimmer):  The Insteon device that changed.
          level (int):  The dimmer level (0->255)
          mode (on_off.Mode):  The on/off mode state.
          reason (str):  The reason the device was triggered.  This is an
                 arbitrary string set into the template variables.
        """
        LOG.info("MQTT received level change %s level: %s %s", device.label,
                 level, reason)

        # For manual mode messages, don't retain them because they don't
        # represent persistent state - they're momentary events.
        retain = False if mode == on_off.Mode.MANUAL else None

        data = self.template_data(level, mode, reason=reason)
        self.msg_state.publish(self.mqtt, data, retain=retain)

    #-----------------------------------------------------------------------
    def _insteon_manual(self, device, manual, reason=""):
        """Device manual mode changed callback.

        This is triggered via signal when the Insteon device starts or stops
        manual mode (holding a button down).  It will publish an MQTT message
        with the new state.

        Args:
          device (device.Dimmer):  The Insteon device that changed.
          manual (on_off.Manual):  The manual mode.
          reason (str):  The reason the device was triggered.  This is an
                 arbitrary string set into the template variables.
        """
        LOG.info("MQTT received manual change %s mode: %s %s", device.label,
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
        LOG.debug("Dimmer message %s %s", message.topic, message.payload)

        # Parse the input MQTT message.
        data = self.msg_on_off.to_json(message.payload)
        LOG.info("Dimmer input command: %s", data)
        try:
            # Tell the device to update it's state.
            is_on, mode = util.parse_on_off(data)
            level = 0 if not is_on else 0xff
            reason = data.get("reason", "")
            self.device.set(level=level, mode=mode, reason=reason)
        except:
            LOG.exception("Invalid switch on/off command: %s", data)

    #-----------------------------------------------------------------------
    def _input_set_level(self, client, data, message):
        """Handle an input level change MQTT message.

        This is called when we receive a message on the level change MQTT
        topic subscription.  Parse the message and pass the command to the
        Insteon device.

        Args:
          client (paho.Client):  The paho mqtt client (self.link).
          data:  Optional user data (unused).
          message:  MQTT message - has attrs: topic, payload, qos, retain.
        """
        LOG.info("Dimmer message %s %s", message.topic, message.payload)

        data = self.msg_level.to_json(message.payload)
        LOG.info("Dimmer input command: %s", data)
        try:
            is_on, mode = util.parse_on_off(data)
            level = 0 if not is_on else int(data.get('level'))
            reason = data.get("reason", "")

            # Tell the device to change it's level.
            self.device.set(level=level, mode=mode, reason=reason)
        except:
            LOG.exception("Invalid dimmer command: %s", data)

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
        LOG.debug("Dimmer message %s %s", message.topic, message.payload)

        # Parse the input MQTT message.
        data = self.msg_scene.to_json(message.payload)
        LOG.info("Dimmer input command: %s", data)
        try:
            # Scenes don't support modes so don't parse that element.
            is_on = util.parse_on_off(data, have_mode=False)
            group = int(data.get('group', 0x01))
            reason = data.get("reason", "")

            # Tell the device to trigger the scene command.
            self.device.scene(is_on, group, reason)
        except:
            LOG.exception("Invalid dimmer command: %s", data)

    #-----------------------------------------------------------------------
