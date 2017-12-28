#===========================================================================
#
# MQTT keypad linc which is a dimmer plus 4 or 8 button remote.
#
#===========================================================================
import functools
from .. import log
from .Dimmer import Dimmer
from .MsgTemplate import MsgTemplate

LOG = log.get_logger()


class KeypadLinc(Dimmer):
    """TODO: doc
    """
    def __init__(self, mqtt, device):
        """TODO: doc
        """
        # Dimmer will handle signals to/from the dimmer load button.
        super().__init__(mqtt, device)

        # Output state change reporting template.
        self.msg_btn_state = MsgTemplate(
            topic='insteon/{{address}}/state/{{button}}',
            payload='{{on_str.lower()}}',
            )

        # Input on/off command template.
        self.msg_btn_on_off = MsgTemplate(
            topic='insteon/{{address}}/set/{{button}}',
            payload='{ "cmd" : "{{value.lower()}}" }',
            )

        device.signal_pressed.connect(self.handle_pressed)

    #-----------------------------------------------------------------------
    def load_config(self, config, qos=None):
        """TODO: doc
        """
        # Load the dimmer configuration from the dimmer area, not the
        # fanlinc area.
        super().load_config(config, qos)

        # Now load the fan control configuration
        data = config.get("keypad_linc", None)
        self.load_keypad_config(data, qos)

    #-----------------------------------------------------------------------
    def load_keypad_config(self, config, qos=None):
        """TODO: doc
        """
        if not config:
            return

        self.msg_btn_state.load_config(config, 'btn_state_topic',
                                       'btn_state_payload', qos)
        self.msg_btn_on_off.load_config(config, 'btn_on_off_topic',
                                        'btn_on_off_payload', qos)

    #-----------------------------------------------------------------------
    def subscribe(self, link, qos):
        """TODO: doc
        """
        super().subscribe(link, qos)

        # We need to subscribe to each button topic so we know which one is
        # which.
        for group in range(1, 9):
            handler = functools.partial(self.handle_set, group=group)
            data = self.template_data(button=group)
            topic = self.msg_btn_on_off.render_topic(data)
            link.subscribe(topic, qos, handler)

    #-----------------------------------------------------------------------
    def unsubscribe(self, link):
        """TODO: doc
        """
        super().unsubscribe(link)

        for group in range(1, 9):
            data = self.template_data(button=group)
            topic = self.msg_btn_on_off.render_topic(data)
            link.unsubscribe(topic)

    #-----------------------------------------------------------------------
    # pylint: disable=arguments-differ
    def template_data(self, level=None, button=None):
        """TODO: doc
        """
        data = {
            "address" : self.device.addr.hex,
            "name" : self.device.name if self.device.name
                     else self.device.addr.hex,
            "button" : button,
            }

        if level is not None:
            data["on"] = 1 if level else 0,
            data["on_str"] = "on" if level else "off"
            data["level_255"] = level
            data["level_100"] = int(100.0 * level / 255.0)

        return data

    #-----------------------------------------------------------------------
    def handle_set(self, client, data, message, group):
        """TODO: doc

        inbound mqtt message for buttons
        """
        LOG.info("KeypadLinc btn %s message %s %s", group, message.topic,
                 message.payload)

        data = self.msg_btn_on_off.to_json(message.payload)
        if not data:
            return

        LOG.info("KeypadLinc btn %s input command: %s", group, data)
        try:
            cmd = data.get('cmd')
            if cmd == 'on':
                self.device.on(group=group)
            elif cmd == 'off':
                self.device.off(group=group)
            else:
                raise Exception("Invalid button cmd input '%s'" % cmd)
        except:
            LOG.exception("Invalid button command: %s", data)
            return

    #-----------------------------------------------------------------------
    def handle_pressed(self, device, group, is_active):
        """Device active button pressed callback.

        This is triggered via signal when the Insteon device button is
        pressed.  It will publish an MQTT message with the button
        number.

        Args:
          device:   (device.Base) The Insteon device that changed.
          group:    (int) The button number 1...n that was pressed.
        """
        LOG.info("MQTT received button press %s = btn %s on %s", device.label,
                 group, is_active)

        level = 0x00 if not is_active else 0xff
        data = self.template_data(level, group)
        self.msg_btn_state.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
