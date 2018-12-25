#===========================================================================
#
# MQTT thermostat sensor device
#
#===========================================================================
from .. import log
from .. import device as IDev
from .MsgTemplate import MsgTemplate

LOG = log.get_logger()


class Thermostat:
    """MQTT Thermostat object.

    This class links an Insteon Thermostat object to MQTT.  Any
    change in the Insteon device will trigger an MQTT message.
    """
    def __init__(self, mqtt, device):
        """Constructor

        Args:
          mqtt:    (Mqtt) the main MQTT interface object.
          device:  The insteon thermostat device object.
        """
        self.mqtt = mqtt
        self.device = device

        # Set up the default templates for the MQTT messages and payloads.
        self.ambient_temp = MsgTemplate(
            topic='insteon/{{address}}/ambient_temp',
            payload='{"temp_f" : {{temp_f}}, "temp_c" : {{temp_c}}}',
            )
        self.fan_state = MsgTemplate(
            topic='insteon/{{address}}/fan_state',
            payload='{{mode}}',
            )
        self.mode_state = MsgTemplate(
            topic='insteon/{{address}}/mode_state',
            payload='{{mode}}',
            )
        self.cool_sp_state = MsgTemplate(
            topic='insteon/{{address}}/cool_sp_state',
            payload='{"temp_f" : {{temp_f}}, "temp_c" : {{temp_c}}}',
            )
        self.heat_sp_state = MsgTemplate(
            topic='insteon/{{address}}/heat_sp_state',
            payload='{"temp_f" : {{temp_f}}, "temp_c" : {{temp_c}}}',
            )
        self.humid_state = MsgTemplate(
            topic='insteon/{{address}}/humid_state',
            payload='{{humid}}',
            )
        self.status_state = MsgTemplate(
            topic='insteon/{{address}}/status_state',
            payload='{{status}}',
            )

        # Receive notifications from the Insteon device when it changes.
        device.signal_ambient_temp_change.connect(self.handle_ambient_temp_change)
        device.signal_fan_mode_change.connect(self.handle_fan_mode_change)
        device.signal_mode_change.connect(self.handle_mode_change)
        device.signal_cool_sp_change.connect(self.handle_cool_sp_change)
        device.signal_heat_sp_change.connect(self.handle_heat_sp_change)
        device.signal_ambient_humid_change.connect(self.handle_ambient_humid_change)
        device.signal_status_change.connect(self.handle_status_change)

    #-----------------------------------------------------------------------
    def load_config(self, config, qos=None):
        """Load values from a configuration data object.

        Args:
          config:   The configuration dictionary to load from.  The object
                    config is stored in config['thermostat'].
          qos:      The default quality of service level to use.
        """
        data = config.get("thermostat", None)
        if not data:
            return

        # Update the MQTT topics and payloads from the config file.
        self.ambient_temp.load_config(data, 'ambient_temp_topic', 'ambient_temp_payload', qos)
        self.fan_state.load_config(data, 'fan_state_topic', 'fan_state_payload', qos)
        self.mode_state.load_config(data, 'mode_state_topic', 'mode_state_payload', qos)
        self.cool_sp_state.load_config(data, 'cool_sp_state_topic', 'cool_sp_state_payload', qos)
        self.heat_sp_state.load_config(data, 'heat_sp_state_topic', 'heat_sp_state_payload', qos)
        self.humid_state.load_config(data, 'humid_state_topic', 'humid_state_payload', qos)
        self.status_state.load_config(data, 'status_state_topic', 'status_state_payload', qos)

    #-----------------------------------------------------------------------
    def subscribe(self, link, qos):
        """Subscribe to any MQTT topics the object needs.

        Args:
          link:   The MQTT network client to use.
          qos:    The quality of service to use.
        """
        # Not handling input messages yet
        pass

    #-----------------------------------------------------------------------
    def unsubscribe(self, link):
        """Unsubscribe to any MQTT topics the object was subscribed to.

        Args:
          link:   The MQTT network client to use.
        """
        pass

    #-----------------------------------------------------------------------
    def handle_ambient_temp_change(self, device, temp_c):
        """Posts to mqtt changes in ambient temperature

        This is triggered via signal when the ambient temp changes.

        Args:
          device:    (device.Base) The Insteon device that changed.
          temp_c:    the temp in Celsius.
        """
        LOG.info("MQTT received temp change %s = %s C", device.label,
                 temp_c)

        # Set up the variables that can be used in the templates.
        data = {
            "address" : device.addr.hex,
            "name" : device.name if device.name else device.addr.hex,
            "temp_c": temp_c,
            "temp_f": round((temp_c * 9) / 5 + 32, 1)
            }

        # Publish topic
        self.ambient_temp.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
    def handle_fan_mode_change(self, device, fan_mode):
        """Posts to mqtt changes in fan mode

        This is triggered via signal when the fan mode change.

        Args:
          device:    (device.Base) The Insteon device that changed.
          fan_mode:  Thermostat.Fan state.
        """
        LOG.info("MQTT received fan mode change %s = %s C", device.label,
                 fan_mode)

        # Set up the variables that can be used in the templates.
        data = {
            "address" : device.addr.hex,
            "name" : device.name if device.name else device.addr.hex,
            "mode": fan_mode.name,
            }

        # Publish topic
        self.fan_state.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
    def handle_mode_change(self, device, mode):
        """Posts to mqtt changes in the hvac mode

        This is triggered via signal when the mode changes.

        Args:
          device:    (device.Base) The Insteon device that changed.
          mode:      Thermostat.Mode state.
        """
        LOG.info("MQTT received mode change %s = %s C", device.label,
                 mode)

        # Set up the variables that can be used in the templates.
        data = {
            "address" : device.addr.hex,
            "name" : device.name if device.name else device.addr.hex,
            "mode": mode.name,
            }

        # Publish topic
        self.mode_state.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
    def handle_cool_sp_change(self, device, temp_c):
        """Posts to mqtt when the cool setpoint changes

        This is triggered via signal when the cool setpoint changes.

        Args:
          device:    (device.Base) The Insteon device that changed.
          temp_c:    the temp in Celsius.
        """
        LOG.info("MQTT received cool setpoint change %s = %s", device.label,
                 temp_c)

        # Set up the variables that can be used in the templates.
        data = {
            "address" : device.addr.hex,
            "name" : device.name if device.name else device.addr.hex,
            "temp_c": round(temp_c, 1),
            "temp_f": round((temp_c * 9) / 5 + 32, 1)
            }

        # Publish topic
        self.cool_sp_state.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
    def handle_heat_sp_change(self, device, temp_c):
        """Posts to mqtt changes in the heat setpoint

        This is triggered via signal when the heat setpoint changes.

        Args:
          device:    (device.Base) The Insteon device that changed.
          temp_c:    the temp in Celsius.
        """
        LOG.info("MQTT received heat setpoint change %s = %s", device.label,
                 temp_c)

        # Set up the variables that can be used in the templates.
        data = {
            "address" : device.addr.hex,
            "name" : device.name if device.name else device.addr.hex,
            "temp_c": round(temp_c, 1),
            "temp_f": round((temp_c * 9) / 5 + 32, 1)
            }

        # Publish topic
        self.heat_sp_state.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
    def handle_ambient_humid_change(self, device, humid):
        """Posts to mqtt changes in the ambient humidity

        This is triggered via signal when the ambient humidity changes.

        Args:
          device:    (device.Base) The Insteon device that changed.
          humid:     (int) the humidity percentage.
        """
        LOG.info("MQTT received humidity change %s = %s", device.label,
                 humid)

        # Set up the variables that can be used in the templates.
        data = {
            "address" : device.addr.hex,
            "name" : device.name if device.name else device.addr.hex,
            "humid": humid
            }

        # Publish topic
        self.humid_state.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
    def handle_status_change(self, device, status):
        """Posts to mqtt changes in the hvac status

        This is triggered via signal when the hvac status changes.

        Args:
          device:    (device.Base) The Insteon device that changed.
          status:    (str)  OFF, HEATING, COOLING
        """
        LOG.info("MQTT received status change %s = %s", device.label,
                 status)

        # Set up the variables that can be used in the templates.
        data = {
            "address" : device.addr.hex,
            "name" : device.name if device.name else device.addr.hex,
            "status": status
            }

        # Publish topic
        self.status_state.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
