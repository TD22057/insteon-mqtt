#===========================================================================
#
# MQTT Motion sensor device
#
#===========================================================================
from .. import log
from .BatterySensor import BatterySensor
from .MsgTemplate import MsgTemplate

LOG = log.get_logger()


class HiddenDoor(BatterySensor):
    """MQTT interface to an Insteon battery powered hidden door sensor.

    This class connects to a device.HiddenDoor object and converts it's
    output state changes to MQTT messages.

    Hidden Door Sensors do support any input commands, but they're sleeping
    until activated so they can't respond to commands unless manually awoke.
    They also remain awake for a short time after reporting a state change,
    so any commands in their queue will be attempted then as well. Hidden
    door sensors support everything that battery sensors do with the
    addition of reporting their battery voltage, reporting their low battery
    threshold level and their configured heart beat interval.
    """
    def __init__(self, mqtt, device):
        """Constructor

        Args:
          mqtt (mqtt.Mqtt):  The MQTT main interface.
          device (device.Motion):  The Insteon object to link to.
        """
        super().__init__(mqtt, device)

        self.msg_battery_voltage = MsgTemplate(
            topic='insteon/{{address}}/battery_voltage',
            payload='{"voltage" : {{batt_volt}}}')

        device.signal_voltage.connect(self._insteon_voltage)

        # This defines the default discovery_class for these devices
        self.default_discovery_cls = "hidden_door"

    #-----------------------------------------------------------------------
    def load_config(self, config, qos=None):
        """Load values from a configuration data object.

        Args:
          config (dict:  The configuration dictionary to load from.  The object
                 config is stored in config['motion'].
          qos (int):  The default quality of service level to use.
        """
        # Load the BatterySensor configuration.
        super().load_config(config, qos)

        data = config.get("hidden_door", None)
        if not data:
            return

        self.msg_battery_voltage.load_config(data, 'battery_voltage_topic',
                                             'battery_voltage_payload', qos)

        # Add our unique topics to the discovery topic map
        topics = {}
        bat_volt = self.msg_battery_voltage
        topics['battery_voltage_topic'] = bat_volt.render_topic(
            self.base_template_data()
        )
        self.rendered_topic_map.update(topics)

    #-----------------------------------------------------------------------
    def template_data_hidden_door(self, is_dawn=None, batt_volt=None,
                                  low_batt_volt=None, hb_interval=None):
        """Create the Jinja templating data variables.

        Args:
          batt_volt (int): value of battery voltage reported in raw insteon
                  level

        Returns:
          dict:  Returns a dict with the variables available for templating.
        """
        # Set up the variables that can be used in the templates.
        data = {
            "address" : self.device.addr.hex,
            "name" : self.device.name if self.device.name
                     else self.device.addr.hex,
            }

        if batt_volt is not None:
            voltage = int(batt_volt)
            data["voltage"] = voltage

        return data

    #-----------------------------------------------------------------------
    def _insteon_voltage(self, device, batt_volt):
        """Device voltage report callback.

        This is triggered via signal when the Insteon device reports a new
        voltage level.  It will publish an MQTT message with the new level.

        Args:
          device (device.Motion):  The Insteon device that changed.
          voltage (int): raw insteon voltage level
        """

        LOG.info("MQTT received battery voltage change %s = %s",
                 device.label, batt_volt)

        # Set up the variables that can be used in the templates.
        data = self.template_data_hidden_door()
        data["batt_volt"] = batt_volt
        self.msg_battery_voltage.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
