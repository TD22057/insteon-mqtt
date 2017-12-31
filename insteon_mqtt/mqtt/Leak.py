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
    """TODO: doc

    This class uses the regular sensor active signal from
    BatterySensor for wet/dry events but we have a different method
    handle_active below to handle the result vs the one in
    BatterySensor.
    """
    def __init__(self, mqtt, device):
        """TODO: doc
        """
        super().__init__(mqtt, device)

        self.msg_wet = MsgTemplate(
            topic='insteon/{{address}}/leak',
            payload='{{state.upper()}}',
            )

    #-----------------------------------------------------------------------
    def load_config(self, config, qos=None):
        """Load values from a configuration data object.

        Args:
          config:   The configuration dictionary to load from.  The object
                    config is stored in config['leak'].
          qos:      The default quality of service level to use.
        """
        super().load_config(config, qos)

        data = config.get("leak", None)
        if not data:
            return

        self.msg_wet.load_config(data, 'wet_dry_topic', 'wet_dry_payload', qos)

    #-----------------------------------------------------------------------
    # pylint: disable=arguments-differ
    def handle_active(self, device, is_wet):
        """Device wet/dry on/off callback.

        This is triggered via signal when the Insteon device detects
        wet or dry.  It will publish an MQTT message with the new
        state.

        Args:
          device:   (device.Base) The Insteon device that changed.
          is_wet:   (bool) True for wet, False for dry.
        """
        LOG.info("MQTT received wet/dry change %s wet= %s", device.label,
                 is_wet)

        data = {
            "address" : device.addr.hex,
            "name" : device.name if device.name else device.addr.hex,
            "is_wet" : 1 if is_wet else 0,
            "is_wet_str" : "on" if is_wet else "off",
            "is_dry" : 0 if is_wet else 1,
            "is_dry_str" : "off" if is_wet else "on",
            "state" : "wet" if is_wet else "dry",
            }

        self.msg_wet.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
