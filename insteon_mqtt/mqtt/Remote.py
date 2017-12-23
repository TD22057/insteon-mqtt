#===========================================================================
#
# MQTT Mini-remote battery powered remote control.
#
#===========================================================================
from .. import log
from .Base import Base
from .MsgTemplate import MsgTemplate

LOG = log.get_logger()


class Remote(Base):
    """TODO: doc
    """
    def __init__(self, mqtt, device):
        """TODO: doc
        """
        super().__init__()

        self.mqtt = mqtt
        self.device = device

        self.msg_state = MsgTemplate(
            topic='insteon/{{address}}/state/{{button}}',
            payload='{{on_str.lower()}}',
            )

        device.signal_pressed.connect(self.handle_pressed)

    #-----------------------------------------------------------------------
    def load_config(self, config, qos=None):
        """TODO: doc
        """
        data = config.get("remote", None)
        if not data:
            return

        self.msg_state.load_config(data, 'state_topic', 'state_payload', qos)

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
        LOG.info("MQTT received button press %s = btn %s", device.label, button)

        data = {
            "address" : device.addr.hex,
            "name" : device.name if device.name else device.addr.hex,
            "button" : button,
            "on" : 1 if is_active else 0,
            "on_str" : "on" if is_active else "off",
            }

        self.msg_state.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
