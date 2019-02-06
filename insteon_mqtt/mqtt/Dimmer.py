#===========================================================================
#
# MQTT dimmer switch device
#
#===========================================================================
from .. import log
from .. import on_off
from .MsgTemplate import MsgTemplate
from .Switch import Switch

LOG = log.get_logger()


class Dimmer(Switch):
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
        # Initialize the Switch attributes but tell the switch to not connect
        # on/off signals since we'll do that here with the dimmer levels.
        super().__init__(mqtt, device, connect_signals=False)

        # Output state change reporting template.
        self.msg_state = MsgTemplate(
            topic='insteon/{{address}}/state',
            payload='{ "state" : "{{on_str.upper()}}", '
                    '"brightness" : {{level_255}} }')

        # self.msg_manual_state inherited from Switch.
        self.msg_manual_state = MsgTemplate(None, None)

        # Input level command template.
        self.msg_level = MsgTemplate(
            topic='insteon/{{address}}/level',
            payload='{ "cmd" : "{{json.state.lower()}}", '
                    '"level" : {{json.brightness}} }')

        # self.msg_scene_on_off inherited from Switch.

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

        # Use the Switch class to load some of our configuration dasta.
        super().load_switch_config(data, qos)

        # Now load the dimmer specific configuration data.
        self.msg_level.load_config(data, 'level_topic', 'level_payload', qos)

    #-----------------------------------------------------------------------
    def subscribe(self, link, qos):
        """Subscribe to any MQTT topics the object needs.

        Subscriptions are used when the object has things that can be
        commanded to change.

        Args:
          link (network.Mqtt):  The MQTT network client to use.
          qos (int):  The quality of service to use.
        """
        # Subscribe to the Switch topics.
        super().subscribe(link, qos)

        # Level changing command messages.
        topic = self.msg_level.render_topic(self.template_data())
        link.subscribe(topic, qos, self._input_set_level)

    #-----------------------------------------------------------------------
    def unsubscribe(self, link):
        """Unsubscribe to any MQTT topics the object was subscribed to.

        Args:
          link (network.Mqtt):  The MQTT network client to use.
        """
        # Unsubscribe from the Switch topics.
        super().unsubscribe(link)

        topic = self.msg_level.render_topic(self.template_data())
        self.mqtt.unsubscribe(topic)

    #-----------------------------------------------------------------------
    # pylint: disable=arguments-differ
    def template_data(self, level=None, mode=on_off.Mode.NORMAL):
        """Create the Jinja templating data variables for on/off messages.

        Args:
          level (int):  The dimmer level.  If None, on/off and levels
                attributes are not added to the data.
          mode (on_off.Mode):  The on/off mode state.

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

        return data

    #-----------------------------------------------------------------------
    def manual_template_data(self, manual):
        """Create the Jinja templating data variables for manual messages.

        Args:
          manual (on_off.Manual):  The manual mode state.

        Returns:
          dict:  Returns a dict with the variables available for templating.
        """
        # Use the basic template to get name and address.
        data = self.template_data()
        data["manual_str"] = str(manual)
        data["manual"] = manual.int_value()
        data["manual_openhab"] = manual.openhab_value()
        return data

    #-----------------------------------------------------------------------
    def _insteon_level_changed(self, device, level, mode=on_off.Mode.NORMAL):
        """Device on/off and dimmer level changed callback.

        This is triggered via signal when the Insteon device goes active or
        inactive.  It will publish an MQTT message with the new state.

        Args:
          device (device.Dimmer):  The Insteon device that changed.
          level (int):  The dimmer level (0->255)
          mode (on_off.Mode):  The on/off mode state.
        """
        LOG.info("MQTT received level change %s level: %s", device.label,
                 level)

        data = self.template_data(level, mode)
        self.msg_state.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
    def _insteon_manual(self, device, manual):
        """Device manual mode changed callback.

        This is triggered via signal when the Insteon device starts or stops
        manual mode (holding a button down).  It will publish an MQTT message
        with the new state.

        Args:
          device (device.Dimmer):  The Insteon device that changed.
          manual (on_off.Manual):  The manual mode.
        """
        LOG.info("MQTT received manual change %s mode: %s", device.label,
                 manual)

        data = self.manual_template_data(manual)
        self.msg_manual_state.publish(self.mqtt, data)

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

        try:
            data = self.msg_level.to_json(message.payload)
            LOG.info("Dimmer input command: %s", data)

            is_on, mode = Switch.parse_json(data)
            level = 0 if not is_on else int(data.get('level'))

            # Tell the device to change it's level.
            self.device.set(level=level, mode=mode)
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

        try:
            # Parse the input MQTT message.
            data = self.msg_scene_on_off.to_json(message.payload)
            LOG.info("Dimmer input command: %s", data)

            is_on, _mode = Switch.parse_json(data)
            group = int(data.get('group', 0x01))

            # Tell the device to trigger the scene command.
            self.device.scene(is_on, group)
        except:
            LOG.exception("Invalid dimmer command: %s", data)

    #-----------------------------------------------------------------------
