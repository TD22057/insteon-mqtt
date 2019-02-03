#===========================================================================
#
# MQTT On/Off outlet device
#
#===========================================================================
import functools
from .. import log
from .. import on_off
from .MsgTemplate import MsgTemplate
from .Switch import Switch

LOG = log.get_logger()


class Outlet:
    """TODO: doc
    """
    def __init__(self, mqtt, device):
        """TODO: doc
        """
        self.mqtt = mqtt
        self.device = device

        # Output state change reporting template.
        self.msg_state = MsgTemplate(
            topic='insteon/{{address}}/state/{{button}}',
            payload='{{on_str.lower()}}')

        # Input on/off command template.
        self.msg_on_off = MsgTemplate(
            topic='insteon/{{address}}/set/{{button}}',
            payload='{ "cmd" : "{{value.lower()}}" }')

        # Input scene on/off command template.
        self.msg_scene = MsgTemplate(
            topic='insteon/{{address}}/scene/{{button}}',
            payload='{ "cmd" : "{{value.lower()}}" }')

        device.signal_active.connect(self.handle_active)

    #-----------------------------------------------------------------------
    def load_config(self, config, qos=None):
        """Load values from a configuration data object.

        Args:
          config:   The configuration dictionary to load from.  The object
                    config is stored in config['switch'].
          qos:      The default quality of service level to use.
        """
        data = config.get("outlet", None)
        if not data:
            return

        self.msg_state.load_config(data, 'state_topic', 'state_payload', qos)
        self.msg_on_off.load_config(data, 'on_off_topic', 'on_off_payload',
                                    qos)
        self.msg_scene.load_config(data, 'scene_on_off_topic',
                                   'scene_on_off_payload', qos)

    #-----------------------------------------------------------------------
    def subscribe(self, link, qos):
        """Subscribe to any MQTT topics the object needs.

        Args:
          link:   The MQTT network client to use.
          qos:    The quality of service to use.
        """
        for group in range(1, 3):
            handler = functools.partial(self.handle_set, group=group)
            data = self.template_data(button=group)

            topic = self.msg_on_off.render_topic(data)
            link.subscribe(topic, qos, handler)

            handler = functools.partial(self.handle_scene, group=group)
            topic = self.msg_scene.render_topic(data)
            link.subscribe(topic, qos, handler)

    #-----------------------------------------------------------------------
    def unsubscribe(self, link):
        """Unsubscribe to any MQTT topics the object was subscribed to.

        Args:
          link:   The MQTT network client to use.
        """
        for group in range(1, 9):
            data = self.template_data(button=group)

            topic = self.msg_on_off.render_topic(data)
            link.unsubscribe(topic)

            topic = self.msg_scene.render_topic(data)
            link.unsubscribe(topic)

    #-----------------------------------------------------------------------
    def template_data(self, is_on=None, button=None, mode=on_off.Mode.NORMAL):
        """TODO: doc
        """
        data = {
            "address" : self.device.addr.hex,
            "name" : self.device.name if self.device.name
                     else self.device.addr.hex,
            "button" : button,
            }

        if is_on is not None:
            data["on"] = 1 if is_on else 0
            data["on_str"] = "on" if is_on else "off"
            data["mode"] = str(mode)
            data["fast"] = 1 if mode == on_off.Mode.FAST else 0
            data["instant"] = 1 if mode == on_off.Mode.INSTANT else 0

        return data

    #-----------------------------------------------------------------------
    def handle_active(self, device, group, is_on, mode=on_off.Mode.NORMAL):
        """Device active on/off callback.

        This is triggered via signal when the Insteon device goes
        active or inactive.  It will publish an MQTT message with the
        new state.

        Args:
          device:   (device.Base) The Insteon device that changed.
          is_active (bool) True for on, False for off.
        """
        LOG.info("MQTT received active change %s = %s", device.label, is_on)

        data = self.template_data(is_on, group, mode)
        self.msg_state.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
    def handle_set(self, client, data, message, group):
        """TODO: doc
        """
        LOG.debug("Outlet btn %s message %s %s", group, message.topic,
                  message.payload)

        # Parse the input MQTT message.
        data = self.msg_on_off.to_json(message.payload)
        LOG.info("Switch input command: %s", data)

        try:
            # Tell the device to update it's state.
            is_on, mode = Switch.parse_json(data)
            self.device.set(level=is_on, group=group, mode=mode)
        except:
            LOG.exception("Invalid switch command: %s", data)

    #-----------------------------------------------------------------------
    def handle_scene(self, client, data, message, group):
        """TODO: doc
        """
        LOG.debug("Outlet btn %s message %s %s", group, message.topic,
                  message.payload)

        # Parse the input MQTT message.
        data = self.msg_scene.to_json(message.payload)
        LOG.info("Outlet input command: %s", data)

        try:
            # Tell the device to trigger the scene command.
            is_on, _mode = Switch.parse_json(data)
            self.device.scene(is_on, group)
        except:
            LOG.exception("Invalid switch command: %s", data)
            return

    #-----------------------------------------------------------------------
