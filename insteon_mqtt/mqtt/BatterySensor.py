#===========================================================================
#
# MQTT battery sensor device
#
#===========================================================================
from .. import log
from .MsgTemplate import MsgTemplate

LOG = log.get_logger()


class BatterySensor:
    """MQTT interface to an Insteon general battery powered sensor.

    This class connects to a device.BatterySensor object and converts it's
    output state changes to MQTT messages.

    Battery sensors don't support any input commands - they're sleeping until
    activated so they can't respond to commands.  Battery sensors have a
    state topic and a low battery topic they will publish to.
    """
    def __init__(self, mqtt, device):
        """Constructor

        Args:
          mqtt (mqtt.Mqtt):  The MQTT main interface.
          device (device.BatterySensor):  The Insteon object to link to.
        """
        self.mqtt = mqtt
        self.device = device

        # Default values for the topics.
        self.msg_state = MsgTemplate(
            topic='insteon/{{address}}/state',
            payload='{{on_str.lower()}}')
        self.msg_battery = MsgTemplate(
            topic='insteon/{{address}}/low_battery',
            payload='{{is_low_str.lower()}}')

        # Connect the signals from the insteon device so we get notified of
        # changes.
        device.signal_on_off.connect(self._insteon_on_off)
        device.signal_low_battery.connect(self._insteon_low_battery)

    #-----------------------------------------------------------------------
    def load_config(self, config, qos=None):
        """Load values from a configuration data object.

        Args:
          config (dict:  The configuration dictionary to load from.  The object
                 config is stored in config['battery_sensor'].
          qos (int):  The default quality of service level to use.
        """
        data = config.get("battery_sensor", None)
        if not data:
            return

        self.msg_state.load_config(data, 'state_topic', 'state_payload', qos)
        self.msg_battery.load_config(data, 'low_battery_topic',
                                     'low_battery_payload', qos)

    #-----------------------------------------------------------------------
    def subscribe(self, link, qos):
        """Subscribe to any MQTT topics the object needs.

        Subscriptions are used when the object has things that can be
        commanded to change.

        Args:
          link (network.Mqtt):  The MQTT network client to use.
          qos (int):  The quality of service to use.
        """
        # There are no input controls for this object so we don't need to
        # subscribe to anything.
        pass

    #-----------------------------------------------------------------------
    def unsubscribe(self, link):
        """Unsubscribe to any MQTT topics the object was subscribed to.

        Args:
          link (network.Mqtt):  The MQTT network client to use.
        """
        pass

    #-----------------------------------------------------------------------
    def template_data(self, is_on=None, is_low=None):
        """Create the Jinja templating data variables.

        Args:
          is_on (bool):  Is the device on or off.  If this is None, on/off
                attributes are not added to the data.
          is_low (bool):  Is the device low battery or not.  If this is None,
                 low battery attributes are not added to the data.

        Returns:
          dict:  Returns a dict with the variables available for templating.
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

        if is_low is not None:
            data["is_low"] = 1 if is_low else 0
            data["is_low_str"] = "on" if is_low else "off"

        return data

    #-----------------------------------------------------------------------
    def _insteon_on_off(self, device, is_on):
        """Device active on/off callback.

        This is triggered via signal when the Insteon device goes on or off.
        It will publish an MQTT message with the new state.

        Args:
          device (device.BatterySensor):  The Insteon device that changed.
          is_on (bool):  True for on, False for off.
        """
        LOG.info("MQTT received on/off change %s on: %s", device.label, is_on)

        data = self.template_data(is_on=is_on)
        self.msg_state.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
    def _insteon_low_battery(self, device, is_low):
        """Device low battery on/off callback.

        This is triggered via signal when the Insteon device detects a low
        batter.  It will publish an MQTT message with the new state.

        Args:
          device (device.BatterySensor):  The Insteon device that changed.
          is_low (bool):  True for low battery, False for not.
        """
        LOG.info("MQTT received low battery %s low: %s", device.label, is_low)

        data = self.template_data(is_low=is_low)
        self.msg_battery.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
