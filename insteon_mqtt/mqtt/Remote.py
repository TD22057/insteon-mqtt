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

        # Output manual state change is off by default.
        self.msg_manual_state = MsgTemplate(None, None)

        device.signal_pressed.connect(self.handle_pressed)
        device.signal_manual.connect(self.handle_manual)

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
        self.msg_manual_state.load_config(data, 'manual_state_topic',
                                          'manual_state_payload', qos)

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
    def template_data(self, button, is_on=None, mode=on_off.Mode.NORMAL):
        """TODO: doc
        """
        # Set up the variables that can be used in the templates.
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
    def manual_template_data(self, button, manual):
        """TODO: doc
        """
        data = self.template_data(button)
        data["manual_str"] = str(manual)
        data["manual"] = manual.int_value()
        data["manual_openhab"] = manual.openhab_value()
        return data

    #-----------------------------------------------------------------------
    def handle_pressed(self, device, button, is_on, mode=on_off.Mode.NORMAL):
        """Device active button pressed callback.

        This is triggered via signal when the Insteon device button is
        pressed.  It will publish an MQTT message with the button
        number.

        Args:
          device:   (device.Base) The Insteon device that changed.
          button:   (int) The button number 1...n that was pressed.
        """
        LOG.info("MQTT received button press %s = btn %s on %s %s",
                 device.label, button, is_on, mode)

        data = self.template_data(button, is_on, mode)
        self.msg_state.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
    def handle_manual(self, device, group, manual):
        """Device manual mode callback.

        This is triggered via signal when the Insteon device goes
        active or inactive.  It will publish an MQTT message with the
        new state.

        Args:
          device:   (device.Base) The Insteon device that changed.
          manual:   (on_off.Manual) The manual mode.
        """
        LOG.info("MQTT received manual button press %s = btn %s %s",
                 device.label, group, manual)

        data = self.manual_template_data(group, manual)
        self.msg_manual_state.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
