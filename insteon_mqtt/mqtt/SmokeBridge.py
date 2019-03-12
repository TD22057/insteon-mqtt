#===========================================================================
#
# MQTT smoke bridge sensor device
#
#===========================================================================
from .. import log
from .. import device as IDev
from .MsgTemplate import MsgTemplate

LOG = log.get_logger()


class SmokeBridge:
    """MQTT interface to an Insteon smoke bridge.

    This class connects to a device.SmokeBridge object and converts it's
    output state changes to MQTT messages.

    A smoke bridge will report it's various sensor (CO, smoke, etc) states.
    """
    def __init__(self, mqtt, device):
        """Constructor

        Args:
          mqtt (mqtt.Mqtt):  The MQTT main interface.
          device (device.SmokeBridge):  The Insteon object to link to.
        """
        self.mqtt = mqtt
        self.device = device

        # Set up the default templates for the MQTT messages and payloads.
        self.msg_smoke = MsgTemplate(
            topic='insteon/{{address}}/smoke',
            payload='{{on_str.lower()}}')
        self.msg_co = MsgTemplate(
            topic='insteon/{{address}}/co',
            payload='{{on_str.lower()}}')
        self.msg_battery = MsgTemplate(
            topic='insteon/{{address}}/battery',
            payload='{{on_str.lower()}}')
        self.msg_error = MsgTemplate(
            topic='insteon/{{address}}/error',
            payload='{{on_str.lower()}}')

        # Receive notifications from the Insteon device when it changes.
        device.signal_on_off.connect(self._insteon_change)

    #-----------------------------------------------------------------------
    def load_config(self, config, qos=None):
        """Load values from a configuration data object.

        Args:
          config (dict:  The configuration dictionary to load from.  The object
                 config is stored in config['smoke_bridge'].
          qos (int):  The default quality of service level to use.
        """
        data = config.get("smoke_bridge", None)
        if not data:
            return

        # Update the MQTT topics and payloads from the config file.
        self.msg_smoke.load_config(data, 'smoke_topic', 'smoke_payload', qos)
        self.msg_co.load_config(data, 'co_topic', 'co_payload', qos)
        self.msg_battery.load_config(data, 'battery_topic', 'battery_payload',
                                     qos)
        self.msg_error.load_config(data, 'error_topic', 'error_payload', qos)

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
    # pylint: disable=arguments-differ
    def template_data(self, type, is_on):
        """Create the Jinja templating data variables for the messages.

        Args:
          type (SmokeBridge.Type):  The condition type code.
          is_on (bool):  True if the condition is set, false otherwise.

        Returns:
          dict:  Returns a dict with the variables available for templating.
        """
        data = {
            "address" : self.device.addr.hex,
            "name" : self.device.name if self.device.name
                     else self.device.addr.hex,
            "on" : 1 if is_on else 0,
            "on_str" : "on" if is_on else "off",
            "type" : type.name.lower(),
            }

        return data

    #-----------------------------------------------------------------------
    def _insteon_change(self, device, type, is_on):
        """Device active condition callback.

        This is triggered via signal when the Insteon device emits a state
        change.  It will publish an MQTT message with the new state.

        Args:
          device (device.SmokeBridge):  The Insteon device that changed.
          type (SmokeBridge.Type):  The condition type code.
          is_on (bool):  True if the condition is set, false otherwise.
        """
        LOG.info("MQTT received active change %s %s = %s", device.label,
                 type, is_on)

        # Set up the variables that can be used in the templates.
        data = self.template_data(type, is_on)

        Type = IDev.SmokeBridge.Type

        # Call the right topic depending on the condition field.
        if type == Type.SMOKE:
            self.msg_smoke.publish(self.mqtt, data)

        elif type == Type.CO:
            self.msg_co.publish(self.mqtt, data)

        elif type == Type.LOW_BATTERY:
            self.msg_battery.publish(self.mqtt, data)

        elif type == Type.ERROR:
            self.msg_error.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
