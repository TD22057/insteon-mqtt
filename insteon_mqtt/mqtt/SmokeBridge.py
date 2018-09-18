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
    """MQTT Smoke bridge object.

    This class links an Insteon smoke bridge object to MQTT.  Any
    change in the Instoen device will trigger an MQTT message.
    """
    def __init__(self, mqtt, device):
        """Constructor

        Args:
          mqtt:    (Mqtt) the main MQTT interface object.
          device:  The insteon smoke bridge device object.
        """
        self.mqtt = mqtt
        self.device = device

        # Set up the default templates for the MQTT messages and payloads.
        self.msg_smoke = MsgTemplate(
            topic='insteon/{{address}}/smoke',
            payload='{{on_str.upper()}}',
            )
        self.msg_co = MsgTemplate(
            topic='insteon/{{address}}/co',
            payload='{{on_str.upper()}}',
            )
        self.msg_battery = MsgTemplate(
            topic='insteon/{{address}}/battery',
            payload='{{on_str.upper()}}',
            )
        self.msg_error = MsgTemplate(
            topic='insteon/{{address}}/error',
            payload='{{on_str.upper()}}',
            )

        # Receive notifications from the Insteon device when it changes.
        device.signal_state_change.connect(self.handle_change)

    #-----------------------------------------------------------------------
    def load_config(self, config, qos=None):
        """Load values from a configuration data object.

        Args:
          config:   The configuration dictionary to load from.  The object
                    config is stored in config['smoke_bridge'].
          qos:      The default quality of service level to use.
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

        Args:
          link:   The MQTT network client to use.
          qos:    The quality of service to use.
        """
        # The smoke bridge doesn't receive commands so there are no
        # input topics to subscribe to.
        pass

    #-----------------------------------------------------------------------
    def unsubscribe(self, link):
        """Unsubscribe to any MQTT topics the object was subscribed to.

        Args:
          link:   The MQTT network client to use.
        """
        pass

    #-----------------------------------------------------------------------
    def handle_change(self, device, condition):
        """Device active condition callback.

        This is triggered via signal when the Insteon device goes
        active or inactive.  It will publish an MQTT message with the
        new state.

        Args:
          device:    (device.Base) The Insteon device that changed.
          condition: SmokeBridge.Type condition code.
        """
        LOG.info("MQTT received active change %s = %s", device.label,
                 condition)

        # Set up the variables that can be used in the templates.
        data = {
            "address" : device.addr.hex,
            "name" : device.name if device.name else device.addr.hex,
            "on" : 1,
            "on_str" : "on",
            }

        Type = IDev.SmokeBridge.Type

        # Clear condition resets the status to off and calls all the
        # conditions.
        clear = condition == Type.CLEAR
        if clear:
            data["on"] = 0
            data["on_str"] = "off"

        # Call the right topic depending on the condition field.
        if clear or condition == Type.SMOKE:
            self.msg_smoke.publish(self.mqtt, data)

        if clear or condition == Type.CO:
            self.msg_co.publish(self.mqtt, data)

        if clear or condition == Type.LOW_BATTERY:
            self.msg_battery.publish(self.mqtt, data)

        if clear or condition == Type.ERROR:
            self.msg_error.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
