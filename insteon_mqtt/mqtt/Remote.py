#===========================================================================
#
# MQTT Mini-remote battery powered remote control.
#
#===========================================================================
from .. import log
from .. import on_off
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
            payload='{{on_str.lower()}}')

        # Fast on/off is handled by msg_state by default.
        self.msg_fast_state = MsgTemplate(None, None)

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
        self.msg_fast_state.load_config(config, 'fast_state_topic',
                                        'fast_state_payload', qos)

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
    def template_data(self, button, is_on, type=on_off.Type.NORMAL):
        """TODO: doc
        """
        # Set up the variables that can be used in the templates.
        data = {
            "address" : self.device.addr.hex,
            "name" : self.device.name if self.device.name
                     else self.device.addr.hex,
            "button" : button,
            "on" : 1 if is_on else 0,
            "on_str" : "on" if is_on else "off",
            "mode" : str(type),
            "fast" : 1 if type == on_off.Type.FAST else 0,
            "instant" : 1 if type == on_off.Type.INSTANT else 0,
            }
        return data

    #-----------------------------------------------------------------------
    def handle_pressed(self, device, button, is_on, type=on_off.Type.NORMAL):
        """Device active button pressed callback.

        This is triggered via signal when the Insteon device button is
        pressed.  It will publish an MQTT message with the button
        number.

        Args:
          device:   (device.Base) The Insteon device that changed.
          button:   (int) The button number 1...n that was pressed.
        """
        LOG.info("MQTT received button press %s = btn %s on %s %s",
                 device.label, button, is_on, type)

        data = self.template_data(button, is_on, type)
        if type is on_off.Type.FAST:
            self.msg_fast_state.publish(self.mqtt, data)

        self.msg_state.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
