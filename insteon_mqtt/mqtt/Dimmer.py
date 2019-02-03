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
    """Insteon dimmer MQTT interface.

    Dimmers will report their state and brightness (level) and can be
    commanded to turn on and off or on at a specific level (0-255).
    """
    def __init__(self, mqtt, device):
        """Constructor

        Args:
          mqtt:     The MQTT main interface.
          device:   The Insteon Dimmer object to link to.
        """
        super().__init__(mqtt, device, handle_active=False)

        # Output state change reporting template.
        self.msg_state = MsgTemplate(
            topic='insteon/{{address}}/state',
            payload='{ "state" : "{{on_str.upper()}}", '
                    '"brightness" : {{level_255}} }')

        # Fast on/off is handled by msg_state by default.
        self.msg_fast_state = MsgTemplate(None, None)

        # Input level command template.
        self.msg_level = MsgTemplate(
            topic='insteon/{{address}}/level',
            payload='{ "cmd" : "{{json.state.lower()}}", '
                    '"level" : {{json.brightness}} }')

        # Input scene on/off command template.
        self.msg_scene_on_off = MsgTemplate(
            topic='insteon/{{address}}/scene',
            payload='{ "cmd" : "{{value.lower()}}" }')

        device.signal_level_changed.connect(self.handle_level_changed)

    #-----------------------------------------------------------------------
    def load_config(self, config, qos=None):
        """Load values from a configuration data object.

        Args:
          config:   The configuration dictionary to load from.  The object
                    config is stored in config['dimmer'].
          qos:      The default quality of service level to use.
        """
        data = config.get("dimmer", None)
        super().load_switch_config(data, qos)
        self.load_dimmer_config(data, qos)

    #-----------------------------------------------------------------------
    def load_dimmer_config(self, config, qos):
        """TODO: doc
        """
        if not config:
            return

        # The Switch base class will load the msg_state template for us.
        self.msg_level.load_config(config, 'level_topic', 'level_payload', qos)
        self.msg_scene_on_off.load_config(config, 'scene_on_off_topic',
                                          'scene_on_off_payload', qos)

    #-----------------------------------------------------------------------
    def subscribe(self, link, qos):
        """Subscribe to any MQTT topics the object needs.

        Args:
          link:   The MQTT network client to use.
          qos:    The quality of service to use.
        """
        super().subscribe(link, qos)

        topic = self.msg_level.render_topic(self.template_data())
        link.subscribe(topic, qos, self.handle_set_level)

        topic = self.msg_scene_on_off.render_topic(self.template_data())
        link.subscribe(topic, qos, self.handle_scene)

    #-----------------------------------------------------------------------
    def unsubscribe(self, link):
        """Unsubscribe to any MQTT topics the object was subscribed to.

        Args:
          link:   The MQTT network client to use.
        """
        super().unsubscribe(link)

        topic = self.msg_level.render_topic(self.template_data())
        self.mqtt.unsubscribe(topic)

        topic = self.msg_scene_on_off.render_topic(self.template_data())
        link.unsubscribe(topic)

    #-----------------------------------------------------------------------
    # pylint: disable=arguments-differ
    def template_data(self, level=None, mode=on_off.Mode.NORMAL):
        """TODO: doc
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
    def handle_level_changed(self, device, level, mode=on_off.Mode.NORMAL):
        """Device active on/off callback.

        This is triggered via signal when the Insteon device goes
        active or inactive.  It will publish an MQTT message with the
        new state.

        Args:
          device:   (device.Base) The Insteon device that changed.
          level     (int) True for on, False for off.
        """
        LOG.info("MQTT received level change %s = %s", device.label, level)

        data = self.template_data(level, mode)
        if mode is on_off.Mode.FAST:
            self.msg_fast_state.publish(self.mqtt, data)

        self.msg_state.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
    def handle_set_level(self, client, data, message):
        """TODO: doc
        """
        LOG.info("Dimmer message %s %s", message.topic, message.payload)

        data = self.msg_level.to_json(message.payload)
        if not data:
            return

        LOG.info("Dimmer input command: %s", data)
        try:
            is_on, mode = Switch.parse_json(data)
            level = 0 if not is_on else int(data.get('level'))
            self.device.set(level=level, mode=mode)
        except:
            LOG.exception("Invalid dimmer command: %s", data)

    #-----------------------------------------------------------------------
    def handle_scene(self, client, data, message):
        """TODO: doc
        """
        LOG.debug("Dimmer message %s %s", message.topic, message.payload)

        # Parse the input MQTT message.
        data = self.msg_scene_on_off.to_json(message.payload)
        LOG.info("Dimmer input command: %s", data)

        try:
            is_on, _mode = Switch.parse_json(data)
            group = int(data.get('group', 0x01))

            # Tell the device to trigger the scene command.
            self.device.scene(is_on, group)

        except:
            LOG.exception("Invalid dimmer command: %s", data)

    #-----------------------------------------------------------------------
