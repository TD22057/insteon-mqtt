#===========================================================================
#
# MQTT Motion sensor device
#
#===========================================================================
from .. import log
from .BatterySensor import BatterySensor
from .MsgTemplate import MsgTemplate

LOG = log.get_logger()


class Motion(BatterySensor):
    """MQTT interface to an Insteon battery powered motion sensor.

    This class connects to a device.Motion object and converts it's output
    state changes to MQTT messages.

    Motion sensors don't support any input commands - they're sleeping until
    activated so they can't respond to commands.  Motion sensors support
    everything that battery sensors do with the addition of a dusk/dawn state
    output (not all Insteon motion sensors will send this status).
    """
    def __init__(self, mqtt, device):
        """Constructor

        Args:
          mqtt (mqtt.Mqtt):  The MQTT main interface.
          device (device.Motion):  The Insteon object to link to.
        """
        super().__init__(mqtt, device)

        self.msg_dawn = MsgTemplate(
            topic='insteon/{{address}}/dawn',
            payload='{{is_dawn_str.lower()}}')

        device.signal_dawn.connect(self._insteon_dawn)

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

        data = config.get("motion", None)
        if not data:
            return

        self.msg_dawn.load_config(data, 'dawn_dusk_topic', 'dawn_dusk_payload',
                                  qos)

        # In versions < 0.6, these were in motion sensor so try and
        # load them to insure old config files still work.
        if "state_topic" in data:
            self.msg_state.load_config(data, 'state_topic', 'state_payload',
                                       qos)
        if "low_battery_topic" in data:
            self.msg_battery.load_config(data, 'low_battery_topic',
                                         'low_battery_payload', qos)

    #-----------------------------------------------------------------------
    def template_data_motion(self, is_dawn=None):
        """Create the Jinja templating data variables.

        Args:
          is_dawn (bool):  Is the dawn (True) or dusk (False).  If this is
                  None, dawn/dusk attributes are not added to the data.

        Returns:
          dict:  Returns a dict with the variables available for templating.
        """
        # Set up the variables that can be used in the templates.
        data = {
            "address" : self.device.addr.hex,
            "name" : self.device.name if self.device.name
                     else self.device.addr.hex,
            }

        if is_dawn is not None:
            data["is_dawn"] = 1 if is_dawn else 0
            data["is_dawn_str"] = "on" if is_dawn else "off"
            data["is_dusk"] = 0 if is_dawn else 1
            data["is_dusk_str"] = "off" if is_dawn else "on"
            data["state"] = "dawn" if is_dawn else "dusk"

        return data

    #-----------------------------------------------------------------------
    def _insteon_dawn(self, device, is_dawn):
        """Device dawn/dusk on/off callback.

        This is triggered via signal when the Insteon device detects dawn or
        dusk.  It will publish an MQTT message with the new state.

        Args:
          device (device.Motion):  The Insteon device that changed.
          is_dawn (bool):  True for dawn, False for dusk.
        """
        LOG.info("MQTT received dawn change %s = %s", device.label, is_dawn)

        data = self.template_data_motion(is_dawn)
        self.msg_dawn.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
