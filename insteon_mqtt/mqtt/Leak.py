#===========================================================================
#
# MQTT leak sensor device
#
#===========================================================================
from .. import log
from .BatterySensor import BatterySensor
from .MsgTemplate import MsgTemplate

LOG = log.get_logger()


class Leak(BatterySensor):
    """Leak battery powered sensor.

    Leak sensors don't support any input commands - they're sleeping until
    activated so they can't respond to commands.  Leak sensors have a state
    topic and a heartbeat topic they will publish to.
    """
    def __init__(self, mqtt, device):
        """Constructor

        Args:
          mqtt (mqtt.Mqtt):  The MQTT main interface.
          device (device.Leak):  The Insteon object to link to.
        """
        super().__init__(mqtt, device)

        # Default values for the topics.
        self.msg_wet = MsgTemplate(
            topic='insteon/{{address}}/wet',
            payload='{{is_wet_str.lower()}}')

        # Connect the two signals from the insteon device so we get notified
        # of changes.
        device.signal_wet.connect(self._insteon_wet)

    #-----------------------------------------------------------------------
    def load_config(self, config, qos=None):
        """Load values from a configuration data object.

        Args:
          config (dict:  The configuration dictionary to load from.  The object
                 config is stored in config['leak'].
          qos (int):  The default quality of service level to use.
        """
        # Load the BatterySensor configuration.
        super().load_config(config, qos)

        data = config.get("leak", None)
        if not data:
            return

        self.msg_wet.load_config(data, 'wet_dry_topic', 'wet_dry_payload', qos)

        # In versions <= 0.7.2, this was in leak sensor so try and
        # load them to insure old config files still work.
        if "heartbeat_topic" in data:
            self.msg_heartbeat.load_config(data, 'heartbeat_topic',
                                           'heartbeat_payload', qos)

    #-----------------------------------------------------------------------
    def template_data_leak(self, is_wet=None):
        """Create the Jinja templating data variables.

        Args:
          is_wet (bool):  Is the device wet or not.  If this is None, wet/dry
                attributes are not added to the data.
          is_heartbeat (bool):  Is the heartbeat active nor not.  If this is
                       None, heartbeat attributes are not added to the data.

        Returns:
          dict:  Returns a dict with the variables available for templating.
        """
        # Set up the variables that can be used in the templates.
        data = {
            "address" : self.device.addr.hex,
            "name" : self.device.name if self.device.name
                     else self.device.addr.hex,
            }

        if is_wet is not None:
            data["is_wet"] = 1 if is_wet else 0
            data["is_wet_str"] = "on" if is_wet else "off"
            data["is_dry"] = 0 if is_wet else 1
            data["is_dry_str"] = "off" if is_wet else "on"
            data["state"] = "wet" if is_wet else "dry"

        return data

    #-----------------------------------------------------------------------
    def _insteon_wet(self, device, is_wet):
        """Device wet/dry on/off callback.

        This is triggered via signal when the Insteon device detects
        wet or dry. It will publish an MQTT message with the new
        state.

        Args:
          device (device.Leak):  The Insteon device that changed.
          is_wet (bool):  True for wet, False for dry.
        """
        LOG.info("MQTT received wet/dry change %s wet= %s", device.label,
                 is_wet)

        data = self.template_data_leak(is_wet)
        self.msg_wet.publish(self.mqtt, data)
