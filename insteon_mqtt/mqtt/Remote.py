#===========================================================================
#
# MQTT Mini-remote battery powered remote control.
#
#===========================================================================
from .. import log
from .MsgTemplate import MsgTemplate

LOG = log.get_logger()


class Remote:
    """TODO: doc
    """
    def __init__(self, mqtt, device):
        """TODO: doc
        """
        self.mqtt = mqtt
        self.device = device

        self.msg_state = MsgTemplate(
            topic='insteon/{{address}}/state/{{button}}',
            payload='{{on_str.lower()}}',
            )

        device.signal_pressed.connect(self.handle_pressed)

    #-----------------------------------------------------------------------
    def load_config(self, config, qos=None):
        """Load values from a configuration data object.

        Args:
          config:   The configuration dictionary to load from.  The object
                    config is stored in config['remote'].
          qos:      The default quality of service level to use.
        """
        data = config.get("remote", None)
        if not data:
            return

        self.msg_state.load_config(data, 'state_topic', 'state_payload', qos)

    #-----------------------------------------------------------------------
    def subscribe(self, link, qos):
        """Subscribe to any MQTT topics the object needs.

        Args:
          link:   The MQTT network client to use.
          qos:    The quality of service to use.
        """
        pass

    #-----------------------------------------------------------------------
    def unsubscribe(self, link):
        """Unsubscribe to any MQTT topics the object was subscribed to.

        Args:
          link:   The MQTT network client to use.
        """
        pass

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

        self.msg_state.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
