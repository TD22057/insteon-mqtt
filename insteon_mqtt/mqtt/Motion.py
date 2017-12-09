#===========================================================================
#
# MQTT Motion sensor device
#
#===========================================================================
from .. import log
from .Base import Base
from .MsgTemplate import MsgTemplate

LOG = log.get_logger()


class Motion(Base):
    """TODO: doc
    """
    def __init__(self, mqtt, device):
        """TODO: doc
        """
        super().__init__()

        self.mqtt = mqtt
        self.device = device

        self.msg_state = MsgTemplate(
            topic = 'insteon/{{address}}/state',
            payload = '{{on_str.lower()}}',
            )
        self.msg_dawn = MsgTemplate(
            topic = 'insteon/{{address}}/dawn',
            payload = '{{is_dawn_str.upper()}}',
            )
        self.msg_battery = MsgTemplate(
            topic = 'insteon/{{address}}/low_battery',
            payload = '{{is_low_str.upper()}}',
            )

        device.signal_active.connect(self.handle_active)
        device.signal_dusk.connect(self.handle_dusk)
        device.signal_low_battery.connect(self.handle_low_battery)

    #-----------------------------------------------------------------------
    def load_config(self, config, qos):
        """TODO: doc
        """
        data = config.get("motion", None)
        if not data:
            return

        self.msg_state.load_config(data, 'state_topic', 'state_payload', qos)
        self.msg_dawn.load_config(data, 'dawn_dusk_topic', 'dawn_dusk_payload',
                                  qos)
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
        LOG.info("MQTT received active change %s '%s' = %s",
                 device.addr, device.name, is_active)

        data = {
            "address" : self.device.addr.hex,
            "name" : self.device.name if self.device.name \
                     else self.device.addr.hex,
            "on" : 1 if is_active else 0,
            "on_str" : "on" if is_active else "off",
            }

        self.msg_state.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
    def handle_dusk(self, device, is_dusk):
        """Device dawn/dusk on/off callback.

        This is triggered via signal when the Insteon device detects
        dawn or dusk.  It will publish an MQTT message with the new
        state.

        Args:
          device:   (device.Base) The Insteon device that changed.
          is_dusk:  (bool) True for dusk, False for dawn.

        """
        LOG.info("MQTT received dusk change %s '%s' = %s",
                 device.addr, device.name, is_dusk)

        data = {
            "address" : device.addr.hex,
            "name" : device.name if device.name else device.addr.hex,
            "is_dawn" : 0 if is_dusk else 1,
            "is_dawn_str" : "off" if is_dusk else "on",
            "is_dusk" : 1 if is_dusk else 0,
            "is_dusk_str" : "on" if is_dusk else "off",
            "state" : "dusk" if is_dusk else "dawn",
            }

        self.msg_dawn.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
    def handle_low_battery(self, device, is_low):
        """Device low battery on/off callback.

        This is triggered via signal when the Insteon device detects a
        low batery It will publish an MQTT message with the new state.

        Args:
          device:   (device.Base) The Insteon device that changed.
          is_low:   (bool) True for low battery, False for not.
        """
        LOG.info("MQTT received low battery %s '%s' = %s",
                 device.addr, device.name, is_low)

        data = {
            "address" : device.addr.hex,
            "name" : device.name if device.name else device.addr.hex,
            "is_low" : 1 if is_low else 0,
            "is_low_str" : "on" if is_low else "off",
            }

        self.msg_battery.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
