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
    """TODO: doc
    """
    def __init__(self, mqtt, device):
        """TODO: doc
        """
        super().__init__(mqtt, device)

        self.msg_dawn = MsgTemplate(
            topic='insteon/{{address}}/dawn',
            payload='{{is_dawn_str.upper()}}',
            )

        device.signal_dawn.connect(self.handle_dawn)

    #-----------------------------------------------------------------------
    def load_config(self, config, qos=None):
        """Load values from a configuration data object.

        Args:
          config:   The configuration dictionary to load from.  The object
                    config is stored in config['motion'].
          qos:      The default quality of service level to use.
        """
        super().load_config(config, qos)

        data = config.get("motion", None)
        if not data:
            return

        self.msg_dawn.load_config(data, 'dawn_dusk_topic', 'dawn_dusk_payload',
                                  qos)

        # In versions < 0.6, these were in motion sensor so try and
        # load them to insure old config files still work.
        if "state_topic" in config:
            self.msg_state.load_config(data, 'state_topic', 'state_payload',
                                       qos)
        if "low_battery_topic" in config:
            self.msg_battery.load_config(data, 'low_battery_topic',
                                         'low_battery_payload', qos)

    #-----------------------------------------------------------------------
    def handle_dawn(self, device, is_dawn):
        """Device dawn/dusk on/off callback.

        This is triggered via signal when the Insteon device detects
        dawn or dusk.  It will publish an MQTT message with the new
        state.

        Args:
          device:   (device.Base) The Insteon device that changed.
          is_dawn:  (bool) True for dawn, False for dusk.
        """
        LOG.info("MQTT received dawn change %s = %s", device.label, is_dawn)

        data = {
            "address" : device.addr.hex,
            "name" : device.name if device.name else device.addr.hex,
            "is_dawn" : 1 if is_dawn else 0,
            "is_dawn_str" : "on" if is_dawn else "off",
            "is_dusk" : 0 if is_dawn else 1,
            "is_dusk_str" : "off" if is_dawn else "on",
            "state" : "dawn" if is_dawn else "dusk",
            }

        self.msg_dawn.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
