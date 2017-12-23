#===========================================================================
#
# MQTT battery sensor device
#
#===========================================================================
from .. import log
from .Base import Base
from .MsgTemplate import MsgTemplate

LOG = log.get_logger()


class BatterySensor(Base):
    """TODO: doc
    """
    def __init__(self, mqtt, device):
        """TODO: doc
        """
        super().__init__()

        self.mqtt = mqtt
        self.device = device

        self.msg_state = MsgTemplate(
            topic='insteon/{{address}}/state',
            payload='{{on_str.lower()}}',
            )
        self.msg_battery = MsgTemplate(
            topic='insteon/{{address}}/low_battery',
            payload='{{is_low_str.upper()}}',
            )

        device.signal_active.connect(self.handle_active)
        device.signal_low_battery.connect(self.handle_low_battery)

    #-----------------------------------------------------------------------
    def load_config(self, config, qos=None):
        """TODO: doc
        """
        data = config.get("battery_sensor", None)
        if not data:
            return

        self.msg_state.load_config(data, 'state_topic', 'state_payload', qos)
        self.msg_battery.load_config(data, 'low_battery_topic',
                                     'low_battery_payload', qos)

    #-----------------------------------------------------------------------
    def handle_active(self, device, is_active):
        """Device active on/off callback.

        This is triggered via signal when the Insteon device goes
        active or inactive.  It will publish an MQTT message with the
        new state.

        Args:
          device:   (device.Base) The Insteon device that changed.
          is_active (bool) True for on, False for off.
        """
        LOG.info("MQTT received active change %s = %s", device.label,
                 is_active)

        data = {
            "address" : self.device.addr.hex,
            "name" : self.device.name if self.device.name
                     else self.device.addr.hex,
            "on" : 1 if is_active else 0,
            "on_str" : "on" if is_active else "off",
            }

        self.msg_state.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
    def handle_low_battery(self, device, is_low):
        """Device low battery on/off callback.

        This is triggered via signal when the Insteon device detects a
        low batery It will publish an MQTT message with the new state.

        Args:
          device:   (device.Base) The Insteon device that changed.
          is_low:   (bool) True for low battery, False for not.
        """
        LOG.info("MQTT received low battery %s = %s", device.label, is_low)

        data = {
            "address" : device.addr.hex,
            "name" : device.name if device.name else device.addr.hex,
            "is_low" : 1 if is_low else 0,
            "is_low_str" : "on" if is_low else "off",
            }

        self.msg_battery.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
