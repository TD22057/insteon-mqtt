#===========================================================================
#
# MQTT keypad linc which is a dimmer plus 4 or 8 button remote.
#
#===========================================================================
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
        super().__init__(mqtt, device)

        self.msg_button = MsgTemplate(
            topic='insteon/{{address}}/state/{{button}}',
            payload='{{on_str.lower()}}',
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

        self.msg_button.load_config(config, 'button_topic', 'button_payload',
                                    qos)

    #-----------------------------------------------------------------------
    def handle_pressed(self, device, button, is_active):
        """Device active button pressed callback.

        This is triggered via signal when the Insteon device button is
        pressed.  It will publish an MQTT message with the button
        number.

        Args:
          device:   (device.Base) The Insteon device that changed.
          button:   (int) The button number 1...n that was pressed.
        """
        LOG.info("MQTT received button press %s = btn %s", device.label,
                 button)

        data = {
            "address" : device.addr.hex,
            "name" : device.name if device.name else device.addr.hex,
            "button" : button,
            "on" : 1 if is_active else 0,
            "on_str" : "on" if is_active else "off",
            }

        self.msg_button.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
