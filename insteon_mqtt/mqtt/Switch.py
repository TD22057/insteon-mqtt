#===========================================================================
#
# MQTT On/Off switch device
#
#===========================================================================
from .. import log
from .MsgTemplate import MsgTemplate
from .. import on_off

LOG = log.get_logger()


class Switch:
    """MQTT on/off switch object.

    This class links an Insteon on/off switch object to MQTT.  Any
    change in the Instoen device will trigger an MQTT message and
    changes can be triggered via MQTT message.

    Some classes that can act like a switch can inherit from this
    class to use the same MQTT templates (see Dimmer).
    """
    #-----------------------------------------------------------------------
    @classmethod
    def parse_json(cls, data):
        """TODO: doc
        """
        cmd = data.get('cmd')
        if cmd == 'on':
            is_on = True
        elif cmd == 'off':
            is_on = False
        else:
            raise Exception("Invalid on/off command input '%s'" % cmd)

        # If mode is present, use that to specify normal/fast/instant.
        # Otherwise look for individual keywords.
        if 'mode' in data:
            mode = on_off.Mode(data.get('mode', 'normal'))
        else:
            mode = on_off.Mode.NORMAL
            if data.get('fast', False):
                mode = on_off.Mode.FAST
            elif data.get('instant', False):
                mode = on_off.Mode.INSTANT

        return is_on, mode

    #-----------------------------------------------------------------------
    def __init__(self, mqtt, device, handle_active=True):
        """Constructor

        Args:
          mqtt:    (Mqtt) the main MQTT interface object.
          device:  The insteon switch device object.
          handle_active:  (bool) If True, connect the signal_active sigma
                          from the device to this class.  If False, the
                          connection is handled elsewhere.  This is
                          commonly used by derived classes.
        """
        self.mqtt = mqtt
        self.device = device

        # Output state change reporting template.
        self.msg_state = MsgTemplate(
            topic='insteon/{{address}}/state',
            payload='{{on_str.lower()}}')

        # Fast on/off is handled by msg_state by default.
        self.msg_fast_state = MsgTemplate(None, None)

        # Input on/off command template.
        self.msg_on_off = MsgTemplate(
            topic='insteon/{{address}}/set',
            payload='{ "cmd" : "{{value.lower()}}" }')

        # Input scene on/off command template.
        self.msg_scene_on_off = MsgTemplate(
            topic='insteon/{{address}}/scene',
            payload='{ "cmd" : "{{value.lower()}}" }')

        # Receive notifications from the Insteon device when it changes.
        if handle_active:
            device.signal_active.connect(self.handle_active)

    #-----------------------------------------------------------------------
    def load_config(self, config, qos=None):
        """Load values from a configuration data object.

        Args:
          config:   The configuration dictionary to load from.  The object
                    config is stored in config['switch'].
          qos:      The default quality of service level to use.
        """
        self.load_switch_config(config.get("switch", None), qos)

    #-----------------------------------------------------------------------
    def load_switch_config(self, config, qos):
        """TODO: doc
        """
        if not config:
            return

        # Update the MQTT topics and payloads from the config file.
        self.msg_state.load_config(config, 'state_topic', 'state_payload', qos)
        self.msg_fast_state.load_config(config, 'fast_state_topic',
                                        'fast_state_payload', qos)
        self.msg_on_off.load_config(config, 'on_off_topic', 'on_off_payload',
                                    qos)
        self.msg_scene_on_off.load_config(config, 'scene_on_off_topic',
                                          'scene_on_off_payload', qos)

    #-----------------------------------------------------------------------
    def subscribe(self, link, qos):
        """Subscribe to any MQTT topics the object needs.

        Args:
          link:   The MQTT network client to use.
          qos:    The quality of service to use.
        """
        topic = self.msg_on_off.render_topic(self.template_data())
        link.subscribe(topic, qos, self.handle_on_off)

        topic = self.msg_scene_on_off.render_topic(self.template_data())
        link.subscribe(topic, qos, self.handle_scene)

    #-----------------------------------------------------------------------
    def unsubscribe(self, link):
        """Unsubscribe to any MQTT topics the object was subscribed to.

        Args:
          link:   The MQTT network client to use.
        """
        topic = self.msg_on_off.render_topic(self.template_data())
        link.unsubscribe(topic)

        topic = self.msg_scene_on_off.render_topic(self.template_data())
        link.unsubscribe(topic)

    #-----------------------------------------------------------------------
    def template_data(self, is_on=None, mode=on_off.Mode.NORMAL):
        """TODO: doc
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

        return data

    #-----------------------------------------------------------------------
    def handle_active(self, device, is_on, mode=on_off.Mode.NORMAL):
        """Device active on/off callback.

        This is triggered via signal when the Insteon device goes
        active or inactive.  It will publish an MQTT message with the
        new state.

        Args:
          device:   (device.Base) The Insteon device that changed.
          is_active (bool) True for on, False for off.
        """
        LOG.info("MQTT received active change %s = %s %s", device.label,
                 is_on, mode)

        data = self.template_data(is_on, mode)

        if mode is on_off.Mode.FAST:
            self.msg_fast_state.publish(self.mqtt, data)

        self.msg_state.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
    def handle_on_off(self, client, data, message):
        """TODO: doc
        """
        LOG.debug("Switch message %s %s", message.topic, message.payload)

        # Parse the input MQTT message.
        data = self.msg_on_off.to_json(message.payload)
        LOG.info("Switch input command: %s", data)

        try:
            # Tell the device to update it's state.
            is_on, mode = Switch.parse_json(data)
            self.device.set(level=is_on, mode=mode)
        except:
            LOG.exception("Invalid switch command: %s", data)
            return

    #-----------------------------------------------------------------------
    def handle_scene(self, client, data, message):
        """TODO: doc
        """
        LOG.debug("Switch message %s %s", message.topic, message.payload)

        # Parse the input MQTT message.
        data = self.msg_scene_on_off.to_json(message.payload)
        LOG.info("Switch input command: %s", data)

        try:
            is_on, _mode = Switch.parse_json(data)
            group = int(data.get('group', 0x01))

            # Tell the device to trigger the scene command.
            self.device.scene(is_on, group)

        except:
            LOG.exception("Invalid switch command: %s", data)
            return

    #-----------------------------------------------------------------------
